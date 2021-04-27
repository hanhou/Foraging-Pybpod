/*
 * A software development kit for Sensapex 2015 series Micromanipulator
 *
 * Copyright (c) 2015-2019, Sensapex Oy
 * All rights reserved.
 *
 * This file is part of 2015 series Sensapex Micromanipulator SDK
 *
 * The Sensapex micromanipulator SDK is free software: you can redistribute
 * it and/or modify it under the terms of the GNU Lesser General Public License
 * as published by the Free Software Foundation, either version 3 of the License,
 * or (at your option) any later version.
 *
 * The Sensapex Micromanipulator SDK is distributed in the hope that it will be
 * useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with the Sensapex micromanipulator SDK. If not, see
 * <http://www.gnu.org/licenses/>.
 *
 */

#include <stdlib.h>
#include <stdio.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdarg.h>
#include <string.h>
#include <errno.h>
#include <sys/timeb.h>
#include <ctype.h>

#include "libump.h"
#include "smcp1.h"


#define LIBUMP_VERSION_STR    "v0.834"
#define LIBUMP_COPYRIGHT      "Copyright (c) Sensapex 2017-2019. All rights reserved"

#define LIBUMP_MAX_MESSAGE_SIZE   1502
#define LIBUMP_ANY_IPV4_ADDR  "0.0.0.0"

typedef unsigned char ump_message[LIBUMP_MAX_MESSAGE_SIZE];

#ifdef _WINDOWS
HRESULT __stdcall DllRegisterServer(void) { return S_OK; }
HRESULT __stdcall DllUnregisterServer(void) { return S_OK; }
#endif

#ifndef __PRETTY_FUNCTION__
#define __PRETTY_FUNCTION__ __func__
#endif

#ifndef LIBUMP_SHARED_DO_NOT_EXPORT
const char rcsid[] = "$Id: Sensapex 2015 series micromanipulator interface " LIBUMP_VERSION_STR " " __DATE__ " " LIBUMP_COPYRIGHT " Exp $";
#endif
#ifdef _WINDOWS
int gettimeofday(struct timeval* t,void* timezone);
#endif
// from linux's sys/times.h

#define __need_clock_t
#include <time.h>
#ifndef _WINDOWS
#include <sys/time.h>
#endif
#ifdef _WINDOWS
/* Structure describing CPU time used by a process and its children.  */
struct tms
  {
    clock_t tms_utime;          /* User CPU time.  */
    clock_t tms_stime;          /* System CPU time.  */
    clock_t tms_cutime;         /* User CPU time of dead children.  */
    clock_t tms_cstime;         /* System CPU time of dead children.  */
  };

/* Store the CPU time used by this process and all its
   dead children (and their dead children) in BUFFER.
   Return the elapsed real time, or (clock_t) -1 for errors.
   All times are in CLK_TCKths of a second.  */
clock_t times (struct tms *__buffer);

typedef long long suseconds_t ;

int gettimeofday(struct timeval* t,void* timezone)
{       struct _timeb timebuffer;
        _ftime( &timebuffer );
        t->tv_sec=timebuffer.time;
        t->tv_usec=1000*timebuffer.millitm;
        return 0;
}

clock_t times (struct tms *__buffer) {

    __buffer->tms_utime = clock();
    __buffer->tms_stime = 0;
    __buffer->tms_cstime = 0;
    __buffer->tms_cutime = 0;
    return __buffer->tms_utime;
}
#endif

// Forward declaration
static int ump_send_msg(ump_state *hndl, const int dev, const int cmd,
                        const int argc,  const int *argv,
                        const int argc2, const int *argv2, // optional second subblock
                        const int respc, int *respv);

const char *ump_get_version()
{   return LIBUMP_VERSION_STR; }

static unsigned long long get_timestamp_us()
{
    struct timeval tv;
    if(gettimeofday(&tv, NULL) < 0)
        return 0;
    return (unsigned long long)tv.tv_sec*1000000LL+(unsigned long long)tv.tv_usec;
}

static unsigned long long get_timestamp_ms()
{
    return get_timestamp_us()/1000LL;
}

static unsigned long long get_elapsed(const unsigned long long ts_ms)
{
    return get_timestamp_ms() - ts_ms;
}

static const char *get_errorstr(const int error_code, char *buf, size_t buf_size)
{    
#ifndef _WINDOWS
    if(strerror_r(error_code, buf, buf_size) < 0)
        snprintf(buf, buf_size, "error code %d", error_code);
#else
    if(error_code == timeoutError)
        strncpy(buf, "timeout", buf_size);
    else
    {
#ifdef _WINDOWS_TEXTUAL_ERRORS // Wrong language and charset combination for non English locales
        LPCWSTR wcBuffer = NULL;
        if(!FormatMessage(FORMAT_MESSAGE_ALLOCATE_BUFFER|FORMAT_MESSAGE_FROM_SYSTEM|FORMAT_MESSAGE_IGNORE_INSERTS,
                         NULL, error_code, MAKELANGID(LANG_NEUTRAL,SUBLANG_DEFAULT),
                         (LPWSTR)&wcBuffer, 0, NULL) || !wcBuffer)
            snprintf(buf, buf_size, "error code %d", error_code);
        else
            WideCharToMultiByte(CP_UTF8, 0, wcBuffer, -1, buf, buf_size, NULL, NULL);
        if(wcBuffer)
            LocalFree((LPWSTR)wcBuffer);
#else
        // Better to print just the number
        snprintf(buf, buf_size, "error code %d", error_code);
#endif // _WINDOWS_TEXTUAL_ERRORS
    }
#endif // _WINDOWS
    return buf;
}

static bool is_invalid_speed_mode(const int mode)
{
    return mode < LIBUMP_TSC_SPEED_MODE_SNAIL || mode > LIBUMP_TSC_SPEED_MODE_PEN;
}

static int is_invalid_storage(const int storage)
{
    return storage < 0 || storage >= 100;
}

ump_error ump_last_error(const ump_state *hndl)
{
    if(!hndl)
        return LIBUMP_NOT_OPEN;
    return hndl->last_error;
}

int ump_last_os_errno(const ump_state *hndl)
{
    if(!hndl)
        return LIBUMP_NOT_OPEN;
    return hndl->last_os_errno;
}

const char *ump_last_os_errorstr(ump_state *hndl)
{
    if(!hndl)
        return ump_errorstr(LIBUMP_NOT_OPEN);
    return hndl->errorstr_buffer;
}

const char *ump_last_errorstr(ump_state *hndl)
{
    static char open_errorstr[80];
    // Special handling for a NULL handle
    if(!hndl)
    {
    #ifndef _WINDOWS
        int error_code = errno;
    #else
        int error_code = GetLastError();
    #endif
        if(!error_code)
            return ump_errorstr(LIBUMP_NOT_OPEN);
        return get_errorstr(error_code, open_errorstr, sizeof(open_errorstr));
    }
    if(strlen(hndl->errorstr_buffer))
        return hndl->errorstr_buffer;
    return ump_errorstr(hndl->last_error);
}

const char *ump_errorstr(const int ret_code)
{
    const char *errorstr;
    if(ret_code >= 0)
        return "No error";
    switch(ret_code)
    {
        case LIBUMP_OS_ERROR:
            errorstr = "Operation system error";
            break;
        case LIBUMP_NOT_OPEN:
            errorstr = "Not opened";
            break;
        case LIBUMP_TIMEOUT:
            errorstr = "Timeout";
            break;
        case LIBUMP_INVALID_ARG:
            errorstr = "Invalid argument";
            break;
        case LIBUMP_INVALID_DEV:
            errorstr = "Invalid device id";
            break;
        case LIBUMP_INVALID_RESP:
            errorstr = "Invalid response";
            break;
        default:
            errorstr = "Unknown error";
            break;
    }
    return errorstr;
}

static void ump_log_print(ump_state *hndl, const int verbose_level, const char *func, const char *fmt, ...)
{
    if(hndl->verbose < verbose_level)
        return;
    va_list args;
    char message[LIBUMP_MAX_LOG_LINE_LENGTH];
    va_start(args, fmt);
    vsnprintf(message, sizeof(message)-1,fmt, args);
    va_end(args);

    if(hndl->log_func_ptr)
        (*hndl->log_func_ptr)(verbose_level, hndl->log_print_arg, func, message);
    else
        fprintf(stderr,"%s: %s\n", func, message);
}

static bool is_cu_dev(const int dev)
{
    return (dev > SMCP1_ALL_MANIPULATORS && dev < SMCP1_ALL_CUS);
}

static bool is_valid_dev(const int dev)
{
    return dev == SMCP1_ALL_CUS || (dev > 0 && dev <= SMCP1_ALL_MANIPULATORS);
}

static int is_invalid_dev(const int dev)
{
    if(is_valid_dev(dev))
        return 0;
    return LIBUMP_INVALID_DEV;
}

static int udp_select(ump_state *hndl, int timeout)
{
    fd_set fdSet;
    struct timeval timev;
    if(hndl->socket == INVALID_SOCKET)
        return -1;
    if(timeout < 0)
        timeout = hndl->timeout;
    timev.tv_sec = timeout/1000;
    timev.tv_usec = (timeout%1000)*1000L;
    FD_ZERO(&fdSet);
    FD_SET(hndl->socket,&fdSet);
    return select(hndl->socket+1, &fdSet, NULL, NULL, &timev );
}

static bool udp_set_address(IPADDR *addr, const char *s)
{
    if(!addr || !s)
        return false;
    addr->sin_family = AF_INET;
    // Poor winsocks does not have even old inet_aton, only
    return((int)(addr->sin_addr.s_addr = inet_addr(s)) != -1);
    // return inet_aton(s, &addr->sin_addr) > 0;
}

static int udp_recv(ump_state *hndl, unsigned char *response, const size_t response_size, IPADDR *from)
{
    int ret;
    if((ret = udp_select(hndl, hndl->timeout)) < 0)
    {
        hndl->last_os_errno = getLastError();
		sprintf(hndl->errorstr_buffer, "select failed - %s", strerror(hndl->last_error));
        return ret;
    }
    else if(!ret)
    {
        hndl->last_os_errno = timeoutError;
        strcpy(hndl->errorstr_buffer,"timeout");
        return ret;
    }

    socklen_t len = sizeof(IPADDR);
    if((ret = recvfrom(hndl->socket, response, response_size, 0,
                          (struct sockaddr *)from, &len)) == SOCKET_ERROR)
    {
        hndl->last_os_errno = getLastError();
        sprintf(hndl->errorstr_buffer,"recvfrom failed - %s", strerror(hndl->last_error));
    }
    return ret;
}

static bool udp_set_sock_opt_addr_reuse(ump_state *hndl)
{
#ifdef _WINDOWS
    char yes = 1;
#else
    int yes = 1;
#endif
    if (setsockopt(hndl->socket, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes)) < 0)
    {
        hndl->last_os_errno = getLastError();
        sprintf(hndl->errorstr_buffer,"address reuse setopt failed - %s", strerror(hndl->last_error));
        return false;
    }
    return true;
}

static bool udp_set_sock_opt_mcast_group(ump_state *hndl, const IPADDR *addr)
{
    struct ip_mreq mreq;
    memset(&mreq, 0, sizeof(mreq));
    mreq.imr_multiaddr = addr->sin_addr;
    setsockopt(hndl->socket, IPPROTO_IP, IP_DROP_MEMBERSHIP, SOCKOPT_CAST &mreq, sizeof(mreq));
    if(setsockopt(hndl->socket, IPPROTO_IP, IP_ADD_MEMBERSHIP, SOCKOPT_CAST &mreq, sizeof(mreq)) < 0)
    {
        hndl->last_os_errno = getLastError();
        sprintf(hndl->errorstr_buffer,"join to multicast group failed - %s", strerror(hndl->last_error));
        return false;
    }
    return true;
}

static bool udp_set_sock_opt_bcast(ump_state *hndl)
{
#ifdef _WINDOWS
    char yes = 1;
#else
    int yes = 1;
#endif
    if(setsockopt(hndl->socket, SOL_SOCKET, SO_BROADCAST, &yes, sizeof(yes)) < 0)
    {
        hndl->last_os_errno = getLastError();
        sprintf(hndl->errorstr_buffer,"broadcast enable failed - %s", strerror(hndl->last_error));
        return false;
    }
    return true;
}

bool udp_get_local_address(ump_state *hndl, IPADDR *addr)
{
    if(!addr)
        return false;
    addr->sin_family = AF_INET;
    // Obtain the local address by connecting an UDP socket
    // TCP/IP stack will resolve the correct network interface
    SOCKET testSocket;

    if((testSocket = socket(AF_INET, SOCK_DGRAM, 0)) == INVALID_SOCKET)
    {
        hndl->last_os_errno = getLastError();
        sprintf(hndl->errorstr_buffer,"socket create failed - %s", strerror(hndl->last_error));
        return false;
    }
    socklen_t addrLen = sizeof(IPADDR);
    if(connect(testSocket,(struct sockaddr *)&hndl->raddr, addrLen) == SOCKET_ERROR)
    {
        hndl->last_os_errno = getLastError();
        sprintf(hndl->errorstr_buffer,"connect failed - %s", strerror(hndl->last_error));
        closesocket(testSocket);
        return false;
    }
    if(getsockname(testSocket,(struct sockaddr *)addr, &addrLen) == SOCKET_ERROR)
    {
        hndl->last_os_errno = getLastError();
        sprintf(hndl->errorstr_buffer,"getsockname failed - %s", strerror(hndl->last_error));
        closesocket(testSocket);
        return false;
    }
    closesocket(testSocket);
    ump_log_print(hndl, 2, __PRETTY_FUNCTION__, "%s:%d", inet_ntoa(addr->sin_addr),ntohs(addr->sin_port));
    return true;
}

static bool udp_is_multicast_address(IPADDR *addr)
{
    return ntohl(addr->sin_addr.s_addr)>>24 == 224;
}

static bool udp_is_loopback_address(IPADDR *addr)
{
    return ntohl(addr->sin_addr.s_addr)>>24 == 127;
}

static bool udp_is_broadcast_address(IPADDR *addr)
{
    return (ntohl(addr->sin_addr.s_addr)&0xff) == 0xff;
}

static bool udp_init(ump_state *hndl, const char *broadcast_address)
{
    bool ok = true;
#ifdef _WINDOWS
    WSADATA wsaData;
    // Initialize winsocket
    if(WSAStartup(MAKEWORD(2, 2), &wsaData))
    {
        hndl->last_os_errno = getLastError();
        sprintf(hndl->errorstr_buffer, "WSAStartup failed (%d)\n", hndl->last_error);
        return 0;
    }
#endif
    if((hndl->socket = socket(AF_INET, SOCK_DGRAM, 0)) == INVALID_SOCKET)
    {
        hndl->last_os_errno = getLastError();
        sprintf(hndl->errorstr_buffer, "socket create failed - %s", strerror(hndl->last_error));
        ok = false;
    }
    if(ok && !udp_set_address(&hndl->raddr, broadcast_address?broadcast_address:LIBUMP_DEF_BCAST_ADDRESS))
    {
        hndl->last_os_errno = getLastError();
        sprintf(hndl->errorstr_buffer, "invalid remote address - %s\n", strerror(hndl->last_error));
        ok = false;
    }
    if(ok && !udp_set_address(&hndl->laddr, LIBUMP_ANY_IPV4_ADDR))
    {
        hndl->last_os_errno = getLastError();
        sprintf(hndl->errorstr_buffer, "invalid local address - %s\n", strerror(hndl->last_error));
        ok = false;
    }
    if(udp_is_loopback_address(&hndl->raddr) && hndl->udp_port == SMCP1_DEF_UDP_PORT)
        hndl->raddr.sin_port = htons(hndl->udp_port-1);
    else
        hndl->raddr.sin_port = htons(hndl->udp_port);
    hndl->laddr.sin_port = htons(hndl->udp_port);

    if(ok)
        ok = udp_set_sock_opt_addr_reuse(hndl);
#ifndef NO_UDP_MULTICAST
    if(ok && udp_is_multicast_address(&hndl->raddr))
        ok = udp_set_sock_opt_mcast_group(hndl, &hndl->raddr);
#endif
    if(ok && udp_is_broadcast_address(&hndl->raddr))
        ok = udp_set_sock_opt_bcast(hndl);
    if(ok && bind(hndl->socket, (struct sockaddr *) &hndl->laddr, sizeof(IPADDR)) == SOCKET_ERROR)
    {
        hndl->last_os_errno = getLastError();
        sprintf(hndl->errorstr_buffer, "bind failed - %s\n", strerror(hndl->last_error));
        ok = false;
    }
#ifdef _WINDOWS
    if(!ok)
        WSACleanup();
#endif
    return ok;
}

static int set_last_error(ump_state *hndl, int code)
{
    char *txt;
    if(hndl)
    {
        hndl->last_error = code;
        switch(code)
        {
        case LIBUMP_NO_ERROR: txt = "No error"; break;
        case LIBUMP_NOT_OPEN: txt = "Communication socket not open"; break;
        case LIBUMP_TIMEOUT:  txt = "Timeout occured"; break;
        case LIBUMP_INVALID_ARG: txt = "Invalid argument"; break;
        case LIBUMP_INVALID_DEV: txt = "Invalid dev id"; break;
        case LIBUMP_INVALID_RESP: txt = "Invalid response received"; break;
        case LIBUMP_OS_ERROR: txt = NULL; break;
        default: txt = "Unknown error";
        }
        if(txt)
            strcpy(hndl->errorstr_buffer, txt);
    }
    return code;
}

static int ump_send(ump_state *hndl, const int dev, const unsigned char *data, int dataSize)
{
    int ret;
    IPADDR to;
    if(dev > 0 && dev < LIBUMP_MAX_MANIPULATORS && hndl->addresses[dev].sin_port && hndl->addresses[dev].sin_family)
        memcpy(&to, &hndl->addresses[dev], sizeof(IPADDR));
    else if(dev == SMCP1_ALL_CUS && hndl->cu_address.sin_port)
        memcpy(&to, &hndl->cu_address, sizeof(IPADDR));
    else
        memcpy(&to, &hndl->raddr, sizeof(IPADDR));

    if(hndl->verbose > 1)
    {
        int i;
        smcp1_frame *header = (smcp1_frame *)data;
        smcp1_subblock_header *sub_block = (smcp1_subblock_header *)(((unsigned char*)data) + SMCP1_FRAME_SIZE);
        int32_t *data_ptr  = (int32_t*)(data) + (SMCP1_FRAME_SIZE + SMCP1_SUB_BLOCK_HEADER_SIZE)/sizeof(int32_t);

        ump_log_print(hndl, 2, __PRETTY_FUNCTION__, "type %d id %d sender %d receiver %d blocks %d options 0x%02X to %s:%d",
                ntohs(header->type), ntohs(header->message_id),
                ntohs(header->sender_id), ntohs(header->receiver_id),
                ntohs(header->sub_blocks),
                (int)ntohl(header->options), inet_ntoa(to.sin_addr), ntohs(to.sin_port));
        if(ntohs(header->sub_blocks))
        {
            int data_size = ntohs(sub_block->data_size);
            ump_log_print(hndl, 3, __PRETTY_FUNCTION__, "sub block size %d type %d", data_size, ntohs(sub_block->data_type));
            for(i = 0; i < data_size; i++, data_ptr++)
                ump_log_print(hndl, 3, __PRETTY_FUNCTION__, " arg%d: %d (0x%02X)%c", i+1, (int)ntohl(*data_ptr), (int)ntohl(*data_ptr), i<data_size-1?',':' ');
        }
    }

    if((ret = sendto(hndl->socket, (char*)data, dataSize, 0,
                (struct sockaddr *) &to, sizeof(IPADDR))) == SOCKET_ERROR)
    {
        hndl->last_os_errno = getLastError();
        sprintf(hndl->errorstr_buffer,"sendto failed - %s\n", strerror(hndl->last_os_errno));
        return set_last_error(hndl, LIBUMP_OS_ERROR);
    }
    return ret;
}

ump_state *ump_open(const char *udp_target_address, const unsigned int timeout, const int group)
{
    int i;
    ump_state *hndl;       
    if(group < 0 || group > 10)
    {
        // LIBUMP_INVALID_ARG
        return NULL;
    }
    if(timeout >= LIBUMP_MAX_TIMEOUT)
    {
        // LIBUMP_INVALID_ARG);
        return NULL;
    }
    if(!(hndl = malloc(sizeof(ump_state))))
        return NULL;
    memset(hndl, 0, sizeof(ump_state));
    hndl->socket = INVALID_SOCKET;
    hndl->udp_port = SMCP1_DEF_UDP_PORT+group;
    hndl->retransmit_count = 3;
    hndl->refresh_time_limit = LIBUMP_DEF_REFRESH_TIME;
    hndl->timeout = timeout;
    for(i = 0; i < LIBUMP_MAX_MANIPULATORS; i++)
    {
        hndl->last_positions[i].x = LIBUMP_ARG_UNDEF;
        hndl->last_positions[i].y = LIBUMP_ARG_UNDEF;
        hndl->last_positions[i].z = LIBUMP_ARG_UNDEF;
        hndl->last_positions[i].w = LIBUMP_ARG_UNDEF;
    }
    hndl->own_id = SMCP1_ALL_PCS - 100 - (get_timestamp_us()&100);
    hndl->timeout = timeout;
    if(!udp_init(hndl, udp_target_address))
    {
        free(hndl);
        return NULL;
    }
    return hndl;
 }

void ump_close(ump_state *hndl)
{
    if(!hndl)
        return;
    if(hndl->socket != INVALID_SOCKET)
    {
        closesocket(hndl->socket);
#ifdef _WINDOWS
        WSACleanup();
#endif
    }
    free(hndl);
}

int ump_set_timeout(ump_state *hndl, const int value)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(value < 0 || value > LIBUMP_MAX_TIMEOUT)
        return set_last_error(hndl, LIBUMP_INVALID_ARG);
    hndl->timeout = value;
    return 0;
}

int ump_set_log_func(ump_state *hndl, const int verbose, ump_log_print_func func, const void *arg)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(verbose < 0)
        return set_last_error(hndl, LIBUMP_INVALID_ARG);
    hndl->verbose = verbose;
    hndl->log_func_ptr = func;
    hndl->log_print_arg = arg;
    return 0;
}

int ump_select_dev(ump_state *hndl, const int dev)
{
    int ret;
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(is_invalid_dev(dev))
        return set_last_error(hndl, LIBUMP_INVALID_DEV);
    // Ping the device
    if((ret = ump_ping(hndl, dev)) < 0)
        return ret;
    hndl->last_device_sent = dev;
    return ump_cu_select_manipulator(hndl, dev);
}

int ump_set_refresh_time_limit(ump_state * hndl, const int value)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(value < LIBUMP_TIMELIMIT_DISABLED || value > 60000)
        return set_last_error(hndl, LIBUMP_INVALID_ARG);
    hndl->refresh_time_limit = value;
    return 0;
}

int ump_is_busy(ump_state *hndl)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    return ump_is_busy_ext(hndl, hndl->last_device_sent);
}

int ump_is_busy_status(const ump_status status)
{
    if(status < 0)
        return status;
    if(status&0xf1)
        return 1;
    return 0;
}

int ump_is_busy_ext(ump_state *hndl, const int dev)
{
    int status = ump_get_status_ext(hndl, dev);
    return ump_is_busy_status(status);
}

ump_status ump_get_status(ump_state *hndl)
{
    if(!hndl) {
        set_last_error(hndl, LIBUMP_NOT_OPEN);
        return LIBUMP_STATUS_READ_ERROR;
    }
    if(is_invalid_dev(hndl->last_device_sent)) {
        set_last_error(hndl, LIBUMP_INVALID_DEV);
        return LIBUMP_STATUS_READ_ERROR;
    }
    int status = ump_get_status_ext(hndl, hndl->last_device_sent);
    if (status <= LIBUMP_STATUS_READ_ERROR)
        return LIBUMP_STATUS_READ_ERROR;
    return (ump_status)status;
}

int ump_get_status_ext(ump_state *hndl, const int dev)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(is_invalid_dev(dev))
        return set_last_error(hndl, LIBUMP_INVALID_DEV);
    return hndl->last_status[dev];
}

int ump_get_drive_status(ump_state *hndl)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(is_invalid_dev(hndl->last_device_sent))
        return set_last_error(hndl, LIBUMP_INVALID_DEV);
    return ump_get_drive_status_ext(hndl, hndl->last_device_sent);
}

int ump_get_drive_status_ext(ump_state *hndl, const int dev)
{
    int drive_status, pwm_status;
    unsigned long long ts, now;

    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(is_invalid_dev(dev))
        return set_last_error(hndl, LIBUMP_INVALID_DEV);

    drive_status = hndl->drive_status[dev];
    pwm_status = hndl->last_status[dev];
    ts = hndl->drive_status_ts[dev];
    now = get_timestamp_ms();

    // Special handling for stuck drive status.
    // If drive status is busy, but pwm status not and 1s elapsed since it was last time,
    // assume drive status notification to be lost and set drive status to completed.
    if(ts && drive_status == LIBUMP_POS_DRIVE_BUSY &&
            !ump_is_busy_status(pwm_status) && now-ts > 1000)
    {
        hndl->drive_status[dev] = LIBUMP_POS_DRIVE_COMPLETED;
        ump_log_print(hndl, 1,__PRETTY_FUNCTION__, "Stuck dev %d drive status, PWM was on %1.1fs ago", dev, (float)(now-ts)/1000.0);
    }
    // update last pwm busy time
    if(ump_is_busy_status(pwm_status))
        hndl->drive_status_ts[dev] = now;
    return hndl->drive_status[dev];
}

static int ump_set_drive_status_ext(ump_state *hndl, const int dev, const int value)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(is_invalid_dev(dev))
        return set_last_error(hndl, LIBUMP_INVALID_DEV);
    hndl->drive_status[dev] = value;
    return 0;
}

int ump_store_mem_current_position(ump_state *hndl)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    return ump_store_mem_current_position_ext(hndl, hndl->last_device_sent, LIBUMP_DEF_STORAGE_ID);
}

int ump_store_mem_current_position_ext(ump_state *hndl, const int dev,
                                       const int storage_id)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(is_invalid_dev(dev))
        return set_last_error(hndl, LIBUMP_INVALID_DEV);
    if(is_invalid_storage(storage_id))
        return set_last_error(hndl, LIBUMP_INVALID_ARG);
    return ump_cmd(hndl, dev, SMCP1_CMD_STORE_MEM, 1, &storage_id);
}

int ump_goto_position(ump_state *hndl, const int x, const int y, const int z, const int w, const int speed)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    return ump_goto_position_ext(hndl, hndl->last_device_sent, x, y, z, w, speed, 0, 0);
}

static int is_invalid_pos(int pos)
{
    if((pos < -1000 || pos > LIBUMP_MAX_POSITION*1000) && pos != SMCP1_ARG_UNDEF)
        return LIBUMP_INVALID_ARG;
    return 0;
}

int ump_goto_position_ext(ump_state *hndl, const int dev, const int x, const int y,
                          const int z, const int w, const int speed, const int mode, const int max_acc)
{
    int ret, args[7], argc = 0;
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(is_invalid_dev(dev))
        return set_last_error(hndl, LIBUMP_INVALID_DEV);
    if(is_invalid_pos(x) || is_invalid_pos(y) || is_invalid_pos(z) || is_invalid_pos(w))
        return set_last_error(hndl, LIBUMP_INVALID_ARG);
    args[argc++] = x;
    args[argc++] = y;
    args[argc++] = z;
    if(w != SMCP1_ARG_UNDEF || speed || mode)
        args[argc++] = w;
    if(speed || mode || max_acc)
        args[argc++] = speed;
    if(mode || max_acc)
        args[argc++] = mode;
    if(max_acc)
        args[argc++] = max_acc;
    ret = ump_cmd(hndl, dev, SMCP1_CMD_GOTO_POS, argc, args);
    ump_set_drive_status_ext(hndl, dev, ret>=0?LIBUMP_POS_DRIVE_BUSY:LIBUMP_POS_DRIVE_FAILED);
    if(ret >= 0)
        hndl->drive_status_ts[dev] = get_timestamp_ms();
    return ret;
}

static int get_max_speed(const int X, const int Y, const int Z, const int W)
{
    int ret = X;
    if(Y > ret) ret = Y;
    if(Z > ret) ret = Z;
    if(W > ret) ret = W;
    return ret;
}

int ump_goto_position_ext2(ump_state *hndl, const int dev,
                           const int x, const int y,
                           const int z, const int w,
                           const int speedX, const int speedY,
                           const int speedZ, const int speedW,
                           const int mode, const int max_acc)
{
    int ret, args[7], args2[4], argc = 0, argc2 = 0;
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(is_invalid_dev(dev))
        return set_last_error(hndl, LIBUMP_INVALID_DEV);
    if(is_invalid_pos(x) || is_invalid_pos(y) || is_invalid_pos(z) || is_invalid_pos(w))
        return set_last_error(hndl, LIBUMP_INVALID_ARG);
    args[argc++] = x;
    args[argc++] = y;
    args[argc++] = z;
    args[argc++] = w;
    // backward compatibility trick for uMs or uMp not supporting second sub block,
    // but just one speed argument shared by all axis
    args[argc++] = get_max_speed(speedX, speedY, speedZ, speedW);
    if(mode || max_acc)
        args[argc++] = mode;
    if(max_acc)
        args[argc++] = max_acc;

    if(x != SMCP1_ARG_UNDEF || y != SMCP1_ARG_UNDEF || z != SMCP1_ARG_UNDEF || w != SMCP1_ARG_UNDEF)
        args2[argc2++] = speedX;
    if(y != SMCP1_ARG_UNDEF || z != SMCP1_ARG_UNDEF || w != SMCP1_ARG_UNDEF)
        args2[argc2++] = speedY;
    if(z != SMCP1_ARG_UNDEF || w != SMCP1_ARG_UNDEF)
        args2[argc2++] = speedZ;
    if(w != SMCP1_ARG_UNDEF)
        args2[argc2++] = speedW;
    ret = ump_send_msg(hndl, dev, SMCP1_CMD_GOTO_POS, argc, args, argc2, args2, 0, NULL);
    ump_set_drive_status_ext(hndl, dev, ret>=0?LIBUMP_POS_DRIVE_BUSY:LIBUMP_POS_DRIVE_FAILED);
    if(ret >= 0)
        hndl->drive_status_ts[dev] = get_timestamp_ms();
    return ret;
}

int ump_goto_virtual_axis_position(ump_state *hndl,const int x_position, const int speed) {
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    return ump_goto_virtual_axis_position_ext(hndl, hndl->last_device_sent, x_position, speed);
}

int ump_goto_virtual_axis_position_ext(ump_state *hndl, const int dev, const int x_position, const int speed) {
    int ret, args[4], argc = 0;
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(is_invalid_dev(dev))
        return set_last_error(hndl, LIBUMP_INVALID_DEV);
    if(is_invalid_pos(x_position) )
        return set_last_error(hndl, LIBUMP_INVALID_ARG);

    args[argc++] = x_position;
    args[argc++] = speed;

    ret = ump_cmd(hndl, dev, SMCP1_CMD_GOTO_VIRTUAL_AXIS_POSITION, argc, args);
    ump_set_drive_status_ext(hndl, dev, ret>=0?LIBUMP_POS_DRIVE_BUSY:LIBUMP_POS_DRIVE_FAILED);
    if(ret >= 0)
        hndl->drive_status_ts[dev] = get_timestamp_ms();
    return ret;
}

int ump_goto_mem_position(ump_state *hndl, const int speed, const int storage_id)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    return ump_goto_mem_position_ext(hndl, hndl->last_device_sent, speed, storage_id, 0);
}

int ump_goto_mem_position_ext(ump_state *hndl, const int dev,
                              const int speed, const int storage_id, const int mode)
{
    int ret, args[3], argc = 0;
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(is_invalid_dev(dev))
        return set_last_error(hndl, LIBUMP_INVALID_DEV);
    if(speed < 1 || speed > 1000) // TODO valid speed range?
        return set_last_error(hndl, LIBUMP_INVALID_ARG);
    if(is_invalid_storage(storage_id))
        return set_last_error(hndl, LIBUMP_INVALID_ARG);
    args[argc++] = storage_id;
    args[argc++] = speed;
    if(mode)
        args[argc++] = mode;
    ret = ump_cmd(hndl, dev, SMCP1_CMD_GOTO_MEM, argc, args);
    ump_set_drive_status_ext(hndl, dev, ret>=0?LIBUMP_POS_DRIVE_BUSY:LIBUMP_POS_DRIVE_FAILED);
    if(ret >= 0)
        hndl->drive_status_ts[dev] = get_timestamp_ms();
    return ret;
}

int ump_get_positions(ump_state *hndl, int *x, int *y, int *z, int *w)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);;
    return ump_get_positions_ext(hndl, hndl->last_device_sent,
                                hndl->refresh_time_limit, x, y, z, w, NULL);
}

int ump_get_speeds(ump_state *hndl, float *x, float *y, float *z, float *w)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);;
    return ump_get_speeds_ext(hndl, hndl->last_device_sent, x, y, z, w, NULL);
}

int ump_read_positions(ump_state *hndl)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    return ump_read_positions_ext(hndl, hndl->last_device_sent, hndl->refresh_time_limit);
}

int ump_get_x_position(ump_state *hndl)
{
    return ump_get_position_ext(hndl, hndl->last_device_sent, 'x');
}

int ump_get_y_position(ump_state *hndl)
{
    return ump_get_position_ext(hndl, hndl->last_device_sent, 'y');
}

int ump_get_z_position(ump_state *hndl)
{
    return ump_get_position_ext(hndl, hndl->last_device_sent, 'z');
}

int ump_get_w_position(ump_state *hndl)
{
    return ump_get_position_ext(hndl, hndl->last_device_sent, 'w');
}

float ump_get_speed_ext(ump_state *hndl, const int dev, const char axis)
{
    if(!hndl || is_invalid_dev(dev))
        return 0.0;
    ump_positions *positions = &hndl->last_positions[dev];
    if(!positions->updated_us)
        return 0.0;
    switch(axis)
    {
    case 'x':
    case 'X':
        return positions->speed_x;
    case 'y':
    case 'Y':
        return positions->speed_y;
    case 'z':
    case 'Z':
        return positions->speed_z;
    case 'w':
    case 'W':
    case '4':
        return positions->speed_w;
    }
    return 0;
}

int ump_get_position_ext(ump_state *hndl, const int dev, const char axis)
{
    if(!hndl || is_invalid_dev(dev))
        return 0;
    ump_positions *positions = &hndl->last_positions[dev];
    if(!positions->updated_us)
        return 0;
    switch(axis)
    {
    case 'x':
    case 'X':
        if(positions->x == LIBUMP_ARG_UNDEF)
            return 0;
        return positions->x;
    case 'y':
    case 'Y':
        if(positions->y == LIBUMP_ARG_UNDEF)
            return 0;
        return positions->y;
    case 'z':
    case 'Z':
        if(positions->z == LIBUMP_ARG_UNDEF)
            return 0;
        return positions->z;
    case 'w':
    case 'W':
    case '4':
        if(positions->w == LIBUMP_ARG_UNDEF)
            return 0;
        return positions->w;
    }
    return 0;
}

int ump_stop_ext(ump_state *hndl, const int dev)
{
    return ump_cmd(hndl, dev, SMCP1_CMD_STOP, 0, NULL);
}

int ump_stop(ump_state *hndl)
{
    return ump_stop_ext(hndl, hndl->last_device_sent);
}

int ump_stop_all(ump_state *hndl)
{
    return ump_stop_ext(hndl, SMCP1_ALL_MANIPULATORS);
}

static int ump_update_position_cache_time(ump_state *hndl, const int sender_id)
{
    int ret = 0;
    ump_positions *positions = &hndl->last_positions[sender_id];
    unsigned long long ts_us = get_timestamp_us();
    if(positions->updated_us)
        ret = (int)(ts_us - positions->updated_us);
    positions->updated_us = ts_us;
    return ret;
}

static int ump_update_positions_cache(ump_state *hndl, const int sender_id, const int axis_index, const int pos_nm, const int time_step_us)
{
    ump_positions *positions = &hndl->last_positions[sender_id];
    int *pos_ptr = NULL;
    float *speed_ptr = NULL;
    int step_nm;

    switch(axis_index)
    {
    case 0:
        pos_ptr = &positions->x;
        speed_ptr = &positions->speed_x;
        break;
    case 1:
        pos_ptr = &positions->y;
        speed_ptr = &positions->speed_y;
        break;
    case 2:
        pos_ptr = &positions->z;
        speed_ptr = &positions->speed_z;
        break;
    case 3:
        pos_ptr = &positions->w;
        speed_ptr = &positions->speed_w;
        break;
    }
    if(!pos_ptr)
        return -1;
    step_nm = pos_nm - *pos_ptr;
    *pos_ptr = pos_nm;
    if(time_step_us > 0)
        *speed_ptr = (float)step_nm *1000.0 / (float)time_step_us;
    else
        *speed_ptr = 0.0;
    return axis_index;
}



int ump_set_slow_speed_mode(ump_state *hndl, const int dev, const int activated){
    if(!hndl || is_invalid_dev(dev))
        return -1;

    return ump_set_ext_feature(hndl,dev,32,activated);
}

int ump_get_slow_speed_mode(ump_state *hndl, const int dev){
    if(!hndl || is_invalid_dev(dev))
        return -1;
    return ump_get_ext_feature(hndl,dev, 32);

}


int ump_get_piezo_voltage(ump_state * hndl, const int dev, const int actuator) {

    int selected_actuator = SMCP1_PARAM_ACT0_PIEZO_INFO;
    if ( actuator == 0 ) selected_actuator = SMCP1_PARAM_ACT0_PIEZO_INFO;
    else if ( actuator == 1 ) selected_actuator = SMCP1_PARAM_ACT1_PIEZO_INFO;
    else if ( actuator == 2 ) selected_actuator = SMCP1_PARAM_ACT2_PIEZO_INFO;
    else if ( actuator == 3 ) selected_actuator = SMCP1_PARAM_ACT3_PIEZO_INFO;

    int piezo = 0;

    if ( ump_get_param(hndl,dev,selected_actuator, &piezo) < 0)
        return -1;

    return piezo;
}

#define UMP_RECEIVE_ACK_GOT  1
#define UMP_RECEIVE_RESP_GOT 2

int ump_recv_ext(ump_state *hndl, ump_message *msg, int *ext_data_type, void *ext_data_ptr)
{
    IPADDR from;
    int receiver_id, sender_id, message_id, type, sub_blocks, data_size = 0, data_type = SMCP1_DATA_VOID, options, status;
    int i, data_type2, data_size2, pos_nm, time_step_us = 0, ext_data_size = 0, ret = 0;
    uint32_t value;
    uint32_t *ext_data = (uint32_t *) ext_data_ptr;
    smcp1_frame *header = (smcp1_frame *)msg;
    smcp1_subblock_header *sub_block2, *sub_block = (smcp1_subblock_header *)((unsigned char*)msg + SMCP1_FRAME_SIZE);

    int32_t *data2_ptr, *data_ptr = (int32_t*)(msg) + (SMCP1_FRAME_SIZE + SMCP1_SUB_BLOCK_HEADER_SIZE)/sizeof(int32_t);

    ump_positions *positions;
    smcp1_frame ack;

    if(ext_data_type != NULL)
        *ext_data_type = -1;

    if(!hndl || hndl->socket == INVALID_SOCKET)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(!msg)
        return set_last_error(hndl, LIBUMP_INVALID_ARG);

    memset(msg, 0, sizeof(ump_message));

    if((ret = udp_recv(hndl, (unsigned char *)msg, sizeof(ump_message), &from)) < 1)
    {
        if(!ret)
            return set_last_error(hndl, LIBUMP_TIMEOUT);
        return set_last_error(hndl, LIBUMP_OS_ERROR);
    }

    if(ret < (int)SMCP1_FRAME_SIZE)
        return set_last_error(hndl, LIBUMP_INVALID_RESP);
    if(header->version != SMCP1_VERSION)
        return set_last_error(hndl, LIBUMP_INVALID_RESP);
    receiver_id = ntohs(header->receiver_id);
    sender_id = ntohs(header->sender_id);
    options = ntohl(header->options);
    type = ntohs(header->type);
    message_id = ntohs(header->message_id);
    sub_blocks = ntohs(header->sub_blocks);

    ump_log_print(hndl, 3,__PRETTY_FUNCTION__, "type %d id %d sender %d receiver %d options 0x%02X from %s:%d",
                  type, message_id, sender_id, receiver_id, options, inet_ntoa(from.sin_addr), ntohs(from.sin_port));
    if(is_valid_dev(sender_id))
        memcpy(&hndl->addresses[sender_id], &from, sizeof(IPADDR));
    else if(is_cu_dev(sender_id))
        memcpy(&hndl->cu_address, &from, sizeof(IPADDR));

    // Filter messages by receiver id, level 1, include broadcasts
    if(receiver_id != SMCP1_ALL_CUS && receiver_id != SMCP1_ALL_PCS &&
            receiver_id != SMCP1_ALL_CUS_OR_PCS && receiver_id != hndl->own_id)
        return set_last_error(hndl, LIBUMP_INVALID_DEV);

    // Notifications, handles also broadcasted ones
    if(sub_blocks > 0 && options & SMCP1_OPT_NOTIFY && is_valid_dev(sender_id))
    {
        data_size = ntohs(sub_block->data_size);
        data_type = ntohs(sub_block->data_type);

        switch(type)
        {
        case SMCP1_NOTIFY_POSITION_CHANGED:
            if(data_size > 0 && (data_type == SMCP1_DATA_INT32 || data_type == SMCP1_DATA_UINT32))
            {
                positions = &hndl->last_positions[sender_id];
                time_step_us = ump_update_position_cache_time(hndl, sender_id);
                // X axis
                pos_nm = ntohl(*data_ptr++);
                ump_update_positions_cache(hndl, sender_id, 0, pos_nm, time_step_us);
                if(data_size > 1)
                {
                    pos_nm = ntohl(*data_ptr++);
                    ump_update_positions_cache(hndl, sender_id, 1, pos_nm, time_step_us);
                }
                if(data_size > 2)
                {
                    pos_nm = ntohl(*data_ptr++);
                    ump_update_positions_cache(hndl, sender_id, 2, pos_nm, time_step_us);
                }
                if(data_size > 3)
                {
                    pos_nm = ntohl(*data_ptr++);
                    ump_update_positions_cache(hndl, sender_id, 3, pos_nm, time_step_us);
                }
                ump_log_print(hndl, 2,__PRETTY_FUNCTION__, "dev %d updated %d position%s %d %d %d %d speeds %1.1f %1.1f %1.1f %1.1fum/s",
                              sender_id, data_size, data_size>1?"s":"",
                              positions->x, positions->y, positions->z, positions->w,
                              positions->speed_x, positions->speed_y, positions->speed_z, positions->speed_w);
            }
            else
                ump_log_print(hndl, 2,__PRETTY_FUNCTION__, "unexpected data type %d or size %d for positions",
                              data_size, ntohs(sub_block->data_type));
            break;
        case SMCP1_NOTIFY_STATUS_CHANGED:
            if(data_size > 0 && (data_type == SMCP1_DATA_INT32 || data_type == SMCP1_DATA_UINT32))
            {
                hndl->last_status[sender_id] = status = ntohl(*data_ptr);
                ump_log_print(hndl, 2,__PRETTY_FUNCTION__, "dev %d updated status %d (0x%08X)", sender_id, status, status);
            }
            break;
        case SMCP1_NOTIFY_GOTO_POS_COMPLETED:
            if(data_size > 0 && (data_type == SMCP1_DATA_INT32 || data_type == SMCP1_DATA_UINT32))
            {
                status = ntohl(*data_ptr);
                if(message_id != hndl->drive_status_id[sender_id])
                {
                    if(status == 0 || status == 2) // Non-zero "not found" erro code at the end of memory position drive
                        hndl->drive_status[sender_id] = LIBUMP_POS_DRIVE_COMPLETED;
                    else
                        hndl->drive_status[sender_id] = LIBUMP_POS_DRIVE_FAILED;
                    ump_log_print(hndl, 2,__PRETTY_FUNCTION__, "dev %d updated drive status %d msg id %d", sender_id, status, message_id);
                    hndl->drive_status_id[sender_id] = message_id;
                }
                else
                    ump_log_print(hndl, 2,__PRETTY_FUNCTION__, "dev %d duplicated drive status %d msg id %d", sender_id, status, message_id);
            }
            break;
        case SMCP1_RD_NOTIFY_TRACE_TEXT:
            if(data_size > 0 && data_type == SMCP1_DATA_CHAR_STRING && ext_data_type != NULL)
            {
                *ext_data_type = SMCP1_RD_NOTIFY_TRACE_TEXT;
                ext_data_size = data_size;
            }

            if(data_size > 0 && data_type == SMCP1_DATA_CHAR_STRING)
            {
                if(data_size > 1 && data_ptr[data_size-2] == '\r')
                   data_ptr[data_size-2] = '\0';
                else if(data_size > 0 && data_ptr[data_size-1] == '\n')
                   data_ptr[data_size-1] = '\0';
                else
                    data_ptr[data_size] = '\0';
                ump_log_print(hndl, 2,__PRETTY_FUNCTION__, "TRACE from %d: %s", sender_id, data_ptr);
            }
            else if(!data_size)
                ump_log_print(hndl, 2,__PRETTY_FUNCTION__, "empty trace data from %d", sender_id);
            else if(data_type != SMCP1_DATA_CHAR_STRING)
                ump_log_print(hndl, 2,__PRETTY_FUNCTION__, "unsupported trace data type %d from %d", data_type, sender_id);
            break;

        // Messages with two subblocks
        case SMCP1_RD_NOTIFY_PIEZO_INFO:
            if(data_size > 0 && (data_type == SMCP1_DATA_INT32 || data_type == SMCP1_DATA_UINT32) && ext_data_type != NULL)
                *ext_data_type = ntohl(*data_ptr);
            break;

        case SMCP1_VERSION:
        case SMCP1_GET_VERSION:
            ump_log_print(hndl, 2,__PRETTY_FUNCTION__,"Version returned", __PRETTY_FUNCTION__);
            break;
        case SMCP1_NOTIFY_CALIBRATE_COMPLETED:
            break;
        default:
            ump_log_print(hndl, 2,__PRETTY_FUNCTION__,"unsupported notification type %d ignored", __PRETTY_FUNCTION__, type);
        }
    }

    // Send ACK if it's requested
    if(options&SMCP1_OPT_REQ_ACK && (receiver_id == hndl->own_id || receiver_id == SMCP1_ALL_CUS || receiver_id == SMCP1_ALL_PCS))
    {
        ump_log_print(hndl, 3,__PRETTY_FUNCTION__, "Sending ACK to %d id %d", type, message_id);
        memcpy(&ack, msg, sizeof(ack));
        ack.sender_id = ntohs(hndl->own_id);
        ack.receiver_id = header->sender_id;
        ack.options = ntohl(options & (~SMCP1_OPT_ACK));
        ack.sub_blocks = 0;
        ump_send(hndl, sender_id, (unsigned char*) &ack, sizeof(ack));
    }

    // Trace text 
    if(ext_data_type != NULL && (*ext_data_type == SMCP1_RD_NOTIFY_TRACE_TEXT ) && ext_data_size)
    {
        if(ext_data_ptr)
            memcpy(ext_data_ptr, data_ptr, ext_data_size);
        return ext_data_size;
    }

    if(sub_blocks > 1 && ext_data_type != NULL && *ext_data_type >= 0)
    {
        sub_block2 = (smcp1_subblock_header *)((unsigned char*)msg + SMCP1_FRAME_SIZE + SMCP1_SUB_BLOCK_HEADER_SIZE + data_size*sizeof(uint32_t));

        data_size2 = ntohs(sub_block2->data_size);
        data_type2 = ntohs(sub_block2->data_type);

        ump_log_print(hndl, 2,__PRETTY_FUNCTION__,"ext data type %d, %d item%s", *ext_data_type, data_size2, data_size2>1?"s":"");

        if((data_type == SMCP1_DATA_INT32 || data_type == SMCP1_DATA_UINT32) && (data_type2 == SMCP1_DATA_INT32 || data_type2 == SMCP1_DATA_UINT32))
        {
            ext_data_size = data_size2;
            data2_ptr = data_ptr + data_size + (SMCP1_SUB_BLOCK_HEADER_SIZE)/sizeof(int32_t);
            for(i = 0; i < data_size2; i++)
            {
                value = ntohl(*data2_ptr++);
                if(i == 0 || i == 1 || i == data_size2-2 || i == data_size2-1)
                    ump_log_print(hndl, 3,__PRETTY_FUNCTION__,"ext_data[%d]\t0x%08x", i, value);
                if(ext_data != NULL)
                    ext_data[i] = value;
            }
        }
        else
            ump_log_print(hndl, 2,__PRETTY_FUNCTION__,"unsupported ext data format %d", data_type2);
        return ext_data_size;
    }

    // For responses or ACKs to our own request, accept only messages sent to our own id
    if(receiver_id != hndl->own_id)
        return set_last_error(hndl, LIBUMP_INVALID_DEV);
    hndl->last_device_received = sender_id;

    // ACK sent to our own message
    if(options&SMCP1_OPT_ACK)
    {
        // ACK to our latest request
        if(message_id == hndl->message_id)
        {
            ump_log_print(hndl, 3,__PRETTY_FUNCTION__, "ACK to %d request %d", type, message_id);
            return UMP_RECEIVE_ACK_GOT;
        }
        ump_log_print(hndl, 2,__PRETTY_FUNCTION__, "ACK to %d id %d while %d expected", type, message_id, hndl->message_id);
        return 0;
    }

    if(!(options&SMCP1_OPT_REQ))
    {
        // Response to our own request
        if(message_id == hndl->message_id)
        {
            ump_log_print(hndl, 3,__PRETTY_FUNCTION__, "response to %d request %d", type, message_id);
            return UMP_RECEIVE_RESP_GOT;
        }
        ump_log_print(hndl, 2,__PRETTY_FUNCTION__, "response to %d id %d while %d expected", type, message_id, hndl->message_id);
        return 0;
    }

    if(options&SMCP1_OPT_REQ) // request to us
    {
        // TODO request to us - at least ping or version query?
        ump_log_print(hndl, 2,__PRETTY_FUNCTION__, "unsupported request type %d", type);
    }
    return 0;
}

int ump_recv(ump_state *hndl, ump_message *msg)
{
    return ump_recv_ext(hndl, msg, NULL, NULL);
}

int ump_receive(ump_state *hndl, const int timelimit)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);

    int ret, count = 0;
    ump_message resp;
    unsigned long long start = get_timestamp_ms();
    do
    {
        if((ret = ump_recv(hndl, &resp)) >= 0)
            count++;
        else if(ret < 0 && ret != LIBUMP_TIMEOUT && ret != LIBUMP_INVALID_DEV)
            return ret;
    } while((int)get_elapsed(start) < timelimit);
    return count;
}

int ump_ping(ump_state *hndl, const int dev)
{
    return ump_cmd(hndl, dev, SMCP1_CMD_PING, 0, NULL);
}

void swap_byte_order(unsigned char *data)
{
    unsigned char *other = data;
    int count = sizeof(data);
    for(int i = 0; i < count; i++)
        *data++ = other[count-(i+1)];
}

int ump_cmd_options(ump_state *hndl,int optionbits)
{
    if(!hndl)
       return set_last_error(hndl, LIBUMP_NOT_OPEN);
    hndl->next_cmd_options |= optionbits;
    return hndl->next_cmd_options;
}

static int ump_send_msg(ump_state *hndl, const int dev, const int cmd,
                        const int argc, const int *argv,
                        const int argc2, const int *argv2, // optional second subblock
                        const int respc, int *respv)
{
    int i, j, resp_data_size, resp_data_type, ret = 0;
    int options = SMCP1_OPT_REQ, req_size = SMCP1_FRAME_SIZE;
    ump_message req, resp;
    smcp1_frame *req_header = (smcp1_frame *)&req;
    smcp1_frame *resp_header = (smcp1_frame *)&resp;
    smcp1_subblock_header *req_sub_header  = (smcp1_subblock_header*)(((unsigned char*)&req) + SMCP1_FRAME_SIZE);
    smcp1_subblock_header *req_sub_header2  = (smcp1_subblock_header*)(((unsigned char*)&req) + SMCP1_FRAME_SIZE +
                                                                       SMCP1_SUB_BLOCK_HEADER_SIZE + argc*sizeof(int32_t));
    int32_t *req_data_ptr  = (int32_t*)(&req) + (SMCP1_FRAME_SIZE + SMCP1_SUB_BLOCK_HEADER_SIZE)/sizeof(int32_t);
    int32_t *req_data_ptr2 = (int32_t*)(&req) + (SMCP1_FRAME_SIZE + 2*SMCP1_SUB_BLOCK_HEADER_SIZE)/sizeof(int32_t) + argc;

    smcp1_subblock_header *resp_sub_header = (smcp1_subblock_header*)(((unsigned char*)&resp) + SMCP1_FRAME_SIZE);
    int32_t *resp_data_ptr = (int32_t*)(&resp) + (SMCP1_FRAME_SIZE + SMCP1_SUB_BLOCK_HEADER_SIZE)/sizeof(int32_t);

    unsigned long start;
    bool ack_received = false, ack_requested = false;
    bool resp_option_requested = false;

    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(is_invalid_dev(dev))
        return set_last_error(hndl, LIBUMP_INVALID_DEV);

    memset(&req, 0, sizeof(req));
    memset(&resp, 0, sizeof(resp));
    req_header->version = SMCP1_VERSION;
    req_header->sender_id = htons(hndl->own_id);
    req_header->receiver_id = htons(dev);
    req_header->type = htons(cmd);
    req_header->message_id = htons(++hndl->message_id);

    if(dev != SMCP1_ALL && dev != SMCP1_ALL_MANIPULATORS &&
            dev != SMCP1_ALL_CUS && dev != SMCP1_ALL_OTHERS &&
            dev != SMCP1_ALL_PCS)
    {
        options |= SMCP1_OPT_REQ_ACK;
        ack_requested = true;
    }
    if(cmd == SMCP1_CMD_GOTO_MEM || cmd == SMCP1_CMD_GOTO_POS)
        options |= SMCP1_OPT_REQ_NOTIFY;
    if(respc)
        options |= SMCP1_OPT_REQ_RESP;

    // If there are additional options set, use them
    if(hndl->next_cmd_options)
    {
        options |= hndl->next_cmd_options;
        if(options & SMCP1_OPT_REQ_RESP && !respc)
            resp_option_requested = true;
        if(options & SMCP1_OPT_REQ_ACK)
            ack_requested = true;
    }

    req_header->options = htonl(options);

    // Reset option flags.
    if (hndl->next_cmd_options)
        hndl->next_cmd_options = 0;

    if(argc > 0 && argv != NULL)
    {
        req_header->sub_blocks = htons(1);
        req_size += sizeof(smcp1_subblock_header) + argc*sizeof(int32_t);
        req_sub_header->data_type = htons(SMCP1_DATA_INT32);
        req_sub_header->data_size = htons(argc);

        for(j = 0; j < argc; j++)
            *req_data_ptr++ = htonl(*argv++);

        if(argc2 > 0 && argv2 != NULL)
        {
            req_header->sub_blocks = htons(2);
            req_size += sizeof(smcp1_subblock_header) + argc2*sizeof(int32_t);
            req_sub_header2->data_type = htons(SMCP1_DATA_INT32);
            req_sub_header2->data_size = htons(argc2);

            for(j = 0; j < argc2; j++)
                *req_data_ptr2++ = htonl(*argv2++);
        }
    }

    // No ACK or RESP requested, just send the message
    if(!ack_requested && (!respc && !resp_option_requested) )
        return ump_send(hndl, dev, (unsigned char *)&req, req_size);

    start = get_timestamp_ms();
    for(i = 0; i < (ack_requested?hndl->retransmit_count:1); i++)
    {
        // Do not resend message if ACK was already got
        if(!ack_received && (ret = ump_send(hndl, dev, (unsigned char *)&req, req_size)) < 0)
            return ret;
        while((ret = ump_recv(hndl, &resp)) >= 0 ||
              ((ret == LIBUMP_TIMEOUT || ret == LIBUMP_INVALID_DEV) &&
              (int)get_elapsed(start) < hndl->timeout))
        {
            ump_log_print(hndl, 4,__PRETTY_FUNCTION__, "ret %d %dms left", ret, (int)(hndl->timeout-get_elapsed(start)));
            if(ret == 1)
                ack_received = true;
            // If not expecting a response, getting ACK is enough.
            if(!respc && ret == 1)
                return 0;
            // Expecting response
            if(respc && ret == 2)
            {
                // A notification may be received between the request and response,
                // a more pedantic response validation is needed.
                if(req_header->type != resp_header->type)
                    continue;
                if(req_header->message_id != resp_header->message_id)
                    continue;
                if(ntohs(resp_header->sub_blocks) < 1)
                {
                    ump_log_print(hndl, 2,__PRETTY_FUNCTION__, "empty response");
                    return set_last_error(hndl, LIBUMP_INVALID_RESP);
                }
                resp_data_size = ntohs(resp_sub_header->data_size);
                resp_data_type = ntohs(resp_sub_header->data_type);
                ump_log_print(hndl, 3,__PRETTY_FUNCTION__, "%d data item%s of type %d",
                              resp_data_size, resp_data_size>1?"s":"",resp_data_type);
                switch(resp_data_type)
                {
                case SMCP1_DATA_UINT32:
                    for(j = 0; j < resp_data_size && j < respc; j++)
                        *respv++ = (int32_t) ntohl(*resp_data_ptr++);
                    break;
                case SMCP1_DATA_INT32:
                    for(j = 0; j < resp_data_size && j < respc; j++)
                        *respv++ = ntohl(*resp_data_ptr++);
                    break;
                case SMCP1_DATA_CHAR_STRING:
                    memcpy(respv, resp_data_ptr, resp_data_size);
                    //resp_data_size=1;
                    break;
                    //memcpy(respv, &resp, resp_data_size);
                    //resp_data_size=1;
                    //break;
                default:
                    ump_log_print(hndl, 2,__PRETTY_FUNCTION__, "unexpected data type %d", resp_data_type);
                    return set_last_error(hndl, LIBUMP_INVALID_RESP);
                }
                return resp_data_size;
            }
        }
    }
    return ret;
}

int ump_cmd_may_cause_movement(const int cmd)
{
    switch(cmd)
    {
    case SMCP1_CMD_INIT_ZERO:
    case SMCP1_CMD_CALIBRATE:
    case SMCP1_CMD_DRIVE_LOOP:
    case SMCP1_CMD_GOTO_MEM:
    case SMCP1_CMD_GOTO_POS:
    case SMCP1_CMD_GOTO_VIRTUAL_AXIS_POSITION:
    case SMCP1_CMD_TAKE_STEP:
    case SMCP1_CMD_TAKE_LEGACY_STEP:
    case SMCP1_CMD_TAKE_JACKHAMMER_STEP:
        return 1;
    }
    return 0;
}

int ump_cmd(ump_state *hndl, const int dev, const int cmd, const int argc, const int *argv)
{
    return ump_send_msg(hndl, dev, cmd, argc, argv, 0, NULL, 0, NULL);
}

int ump_cmd_ext(ump_state *hndl, const int dev, const int cmd, const int argc, const int *argv, int respsize,int *response)
{
    return ump_send_msg(hndl, dev, cmd, argc, argv, 0, NULL, respsize, response);
}

int ump_set_param(ump_state *hndl, const int dev, const int param_id, const int value)
{
    int args[2];
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    args[0] = param_id;
    args[1] = value;
    return ump_cmd(hndl, dev, SMCP1_SET_PARAMETER, 2, args);
}

int ump_get_param(ump_state *hndl, const int dev, const int param_id, int *value)
{
    int ret, resp[2];
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);

    if((ret = ump_send_msg(hndl, dev, SMCP1_GET_PARAMETER, 1, &param_id, 0, NULL, 2, resp)) < 0)
        return ret;
    if(resp[0] != param_id || ret != 2)
        return set_last_error(hndl, LIBUMP_INVALID_RESP);
    *value = resp[1];
    return 1;
}

int ump_set_feature(ump_state *hndl, const int dev, const int feature_id, const int value)
{
    int args[2];
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);

    args[0] = feature_id;
    args[1] = value;
    return ump_cmd(hndl, dev, SMCP1_SET_FEATURE, 2, args);
}

int ump_set_ext_feature(ump_state *hndl, const int dev, const int feature_id, const int value)
{
    int args[2];
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);

    args[0] = feature_id;
    args[1] = value;
    return ump_cmd(hndl, dev, SMCP1_SET_EXT_FEATURE, 2, args);
}

int ump_take_jackhammer_step(ump_state *hndl, const int axis, const int iterations, const int pulse1_step_count, const int pulse1_step_size, int pulse2_step_count, const int pulse2_step_size)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    return ump_take_jackhammer_step_ext(hndl,hndl->last_device_sent, axis, iterations,  pulse1_step_count,  pulse1_step_size,  pulse2_step_count,  pulse2_step_size);
}

int ump_take_jackhammer_step_ext(ump_state *hndl, const int dev, const int axis, const int iterations, const int pulse1_step_count, const int pulse1_step_size, int pulse2_step_count, const int pulse2_step_size)
{
    int args[6], argc = 0;
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);

    args[argc++] = axis;
    args[argc++] = iterations;
    args[argc++] = pulse1_step_count;
    args[argc++] = pulse1_step_size;
    args[argc++] = pulse2_step_count;
    args[argc++] = pulse2_step_size;

    return ump_cmd(hndl, dev, SMCP1_CMD_TAKE_JACKHAMMER_STEP, argc, args);
}

int ump_cmd_get_axis_angle(ump_state *hndl, const int dev, const int actuator, const int layer) {
    int args[2], argc = 0;
    int resp[2];
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);

    args[argc++] = actuator;
    args[argc++] = layer;

    if(ump_send_msg(hndl, dev, SMCP1_CMD_GET_AXIS_ANGLE, argc, args, 0, NULL, 1, &resp[0]) < 0)
        return 0;
    return resp[0];

}

int ump_take_step(ump_state *hndl, const int x, const int y, const int z, const int w, const int speed)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    return ump_take_step_ext(hndl, hndl->last_device_sent, x, y, z, w, speed, speed, speed, speed);
}

int ump_take_step_ext(ump_state *hndl, const int dev,
                      const int step_x, const int step_y, const int step_z, const int step_w,
                      const int speed_x, const int speed_y, const int speed_z, const int speed_w)
{
    int args[9], argc = 0;
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
#ifdef USING_LEGACY_OPENLOOP_STEPS
    if(is_invalid_speed_mode(speed_x))
        return set_last_error(hndl, LIBUMP_INVALID_ARG);
    args[argc++] = speed_x;
    args[argc++] = step_x;
    if(step_y || step_z || step_w)
        args[argc++] = step_y;
    if(step_z || step_w)
        args[argc++] = step_z;
    if(step_w)
        args[argc++] = step_w;
    (void) speed_y;
    (void) speed_z;
    (void) speed_w;
    // TODO: SMCP1_CMD_TAKE_STEP instead of SMCP1_CMD_TAKE_LEGACY_STEP
    return ump_cmd(hndl, dev, SMCP1_CMD_TAKE_LEGACY_STEP, argc, args);
#else
    if(step_x && !speed_x)
        return set_last_error(hndl, LIBUMP_INVALID_ARG);
    if(step_y && !speed_y)
        return set_last_error(hndl, LIBUMP_INVALID_ARG);
    if(step_z && !speed_z)
        return set_last_error(hndl, LIBUMP_INVALID_ARG);
    if(step_w && !speed_w)
        return set_last_error(hndl, LIBUMP_INVALID_ARG);
    args[argc++] = step_x;
    args[argc++] = step_y;
    args[argc++] = step_z;
    args[argc++] = step_w;
    args[argc++] = speed_x;
    args[argc++] = speed_y;
    args[argc++] = speed_z;
    args[argc++] = speed_w;

        // CLS MODE SELECTION
    int clsMode = figure_cls_mode(step_x,step_y,step_z,step_w,
                    speed_x,speed_y,speed_z, speed_w);
    if (clsMode >= 0){
        args[argc++] = clsMode;

    } else
      args[argc++]=0;

    return ump_cmd(hndl, dev, SMCP1_CMD_TAKE_STEP, argc, args);
#endif
}

int ump_get_feature(ump_state *hndl, const int dev, const int feature_id)
{
    int ret, resp[2];
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);

    if((ret = ump_send_msg(hndl, dev, SMCP1_GET_FEATURE, 1, &feature_id, 0, NULL, 2, resp)) < 0)
        return ret;
    if(resp[0] != feature_id || ret != 2)
        return set_last_error(hndl, LIBUMP_INVALID_RESP);
    return resp[1];
}

int ump_get_ext_feature(ump_state *hndl, const int dev, const int feature_id){
    int ret, resp[2];
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);

    if((ret = ump_send_msg(hndl, dev, SMCP1_GET_EXT_FEATURE, 1, &feature_id, 0, NULL, 2, resp)) < 0)
        return ret;
    if(resp[0] != feature_id || ret != 2)
        return set_last_error(hndl, LIBUMP_INVALID_RESP);
    return resp[1];
}

int ump_get_feature_mask(ump_state *hndl, const int dev, const int feature_id)
{
    int ret, resp[2];
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);

    if(is_invalid_dev(dev))
        return set_last_error(hndl, LIBUMP_INVALID_DEV);

     if((ret = ump_send_msg(hndl, dev, SMCP1_CMD_GET_FEATURE_MASK, 1, &feature_id, 0, NULL, 2, resp)) < 0)
        return ret;

    if(resp[0] != feature_id || ret != 2)
        return set_last_error(hndl, LIBUMP_INVALID_RESP);
    return resp[1];

}

int ump_get_feature_functionality(ump_state *hndl, const int dev, const int feature_id)
{
    int ret, resp[2];
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);

    if((ret = ump_send_msg(hndl, dev, SMCP1_CMD_GET_FEATURE_FUNCTIONALITY, 1, &feature_id, 0, NULL, 2, resp)) < 0)
        return ret;
    if(resp[0] != feature_id || ret != 2)
        return set_last_error(hndl, LIBUMP_INVALID_RESP);
    return resp[1];
}

int ump_read_version(ump_state *hndl, int *version, const int size)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);;
    return ump_read_version_ext(hndl, hndl->last_device_sent, version, size);
}

int ump_read_version_ext(ump_state * hndl, const int dev,
                         int *version, const int size)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(is_invalid_dev(dev))
        return set_last_error(hndl, LIBUMP_INVALID_DEV);
    return ump_send_msg(hndl, dev, SMCP1_GET_VERSION, 0, NULL, 0, NULL, size, version);
}

int ump_cu_read_rwx_version(ump_state *hndl, int *version, const int size)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(!version || size < 1)
        return set_last_error(hndl, LIBUMP_INVALID_ARG);
    return ump_send_msg(hndl, SMCP1_ALL_CUS, SMCP1_CU_GET_RWX_FW_VERSION, 0, NULL, 0, NULL, size, version);
}

int ump_get_axis_count(ump_state *hndl, const int dev)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);;
    return ump_get_axis_count_ext(hndl, dev);
}

int ump_get_axis_count_ext(ump_state *hndl, const int dev)
{
    int ret, value = 0;
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(is_invalid_dev(dev))
        return set_last_error(hndl, LIBUMP_INVALID_DEV);
    if((ret = ump_get_param(hndl, dev, SMCP1_PARAM_AXIS_COUNT, &value)) < 0)
        return ret;
    return value;
}

int ump_get_positions_ext(ump_state *hndl, const int dev, const int time_limit,
                         int *x, int *y, int *z, int *w, int *elapsedptr)
{
    int resp[4], ret = 0;
    ump_positions *positions;
    unsigned long start, elapsed;

    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(is_invalid_dev(dev))
        return set_last_error(hndl, LIBUMP_INVALID_DEV);

    positions = &hndl->last_positions[dev];

    elapsed = get_elapsed(positions->updated_us/1000LL);
    // Obtain positions from the cache if values are new enough
    // Position notification carry always at least X-axis position - but typically only three.
    // requiring also w-axis was systematically wrong for 3 axis manipulator or uMs and values
    // were requested every time causing unnecessary IP packets
    if((elapsed < (unsigned long)time_limit || time_limit == LIBUMP_TIMELIMIT_CACHE_ONLY) && time_limit != LIBUMP_TIMELIMIT_DISABLED)
    {
        if(positions->x != LIBUMP_ARG_UNDEF && x) {
            *x = positions->x;
            ret++;
        }
        if(positions->y != LIBUMP_ARG_UNDEF && y) {
            *y = positions->y;
            ret++;
        }
        if(positions->z != LIBUMP_ARG_UNDEF && z) {
            *z = positions->z;
            ret++;
        }
        if(positions->w != LIBUMP_ARG_UNDEF && w) {
            *w = positions->w;
            ret++;
        }
        if(elapsedptr)
            *elapsedptr = elapsed;
        if(ret > 0)
            return ret;
    }
    // Too old or missing positions, request them from the manipulator
    memset(resp, 0, sizeof(resp));
    start = get_timestamp_ms();
    if((ret = ump_send_msg(hndl, dev, SMCP1_GET_POSITIONS, 0, NULL, 0, NULL, 4, resp)) > 0)
    {
        int time_step = ump_update_position_cache_time(hndl, dev);
        ump_update_positions_cache(hndl, dev, 0, resp[0], time_step);
        if(x)
            *x = positions->x != LIBUMP_ARG_UNDEF?positions->x:0;
        if(ret > 1)
        {
            ump_update_positions_cache(hndl, dev, 1, resp[1], time_step);
            if(y)
                *y = positions->x != LIBUMP_ARG_UNDEF?positions->y:0;
        }
        if(ret > 2)
        {
            ump_update_positions_cache(hndl, dev, 2, resp[2], time_step);
            if(z)
                *z = positions->z != LIBUMP_ARG_UNDEF?positions->z:0;
        }
        if(ret > 3)
        {
            ump_update_positions_cache(hndl, dev, 3, resp[3], time_step);
            if(w)
                *w = positions->w != LIBUMP_ARG_UNDEF?positions->w:0;
        }
        positions->updated_us = get_timestamp_us();
    }
    if(elapsedptr && positions->updated_us)
        *elapsedptr = get_elapsed(start);
    return ret;
}

int ump_get_speeds_ext(ump_state *hndl, const int dev, float *x, float *y, float *z, float *w, int *elapsedptr)
{
    int ret = 0;
    ump_positions *positions;
    unsigned long elapsed;

    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(is_invalid_dev(dev))
        return set_last_error(hndl, LIBUMP_INVALID_DEV);

    positions = &hndl->last_positions[dev];
    elapsed = get_elapsed(positions->updated_us/1000LL);

    if(x) {
        *x = positions->speed_x;
        ret++;
    }
    if(y) {
        *y = positions->speed_y;
        ret++;
    }
    if(z) {
        *z = positions->speed_z;
        ret++;
    }
    if(w) {
        *w = positions->speed_w;
        ret++;
    }

    if(elapsedptr)
        *elapsedptr = elapsed;
    return ret;
}

int ump_read_positions_ext(ump_state *hndl, const int dev, const int time_limit)
{
    int resp[4], ret = 0;
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(is_invalid_dev(dev))
        return set_last_error(hndl, LIBUMP_INVALID_DEV);

    ump_positions *positions = &hndl->last_positions[dev];
    unsigned long elapsed = get_elapsed(positions->updated_us/1000LL);
    // Use values from the cache if new enough
    if((elapsed < (unsigned long)time_limit || time_limit == LIBUMP_TIMELIMIT_CACHE_ONLY) && time_limit != LIBUMP_TIMELIMIT_DISABLED)
    {
        if(hndl->last_positions[dev].x != LIBUMP_ARG_UNDEF)
            ret++;
        if(hndl->last_positions[dev].y != LIBUMP_ARG_UNDEF)
            ret++;
        if(hndl->last_positions[dev].z != LIBUMP_ARG_UNDEF)
            ret++;
        if(hndl->last_positions[dev].w != LIBUMP_ARG_UNDEF)
            ret++;
        if(ret > 0)
            return ret;
    }

    // Request positions from the manipulator
    memset(resp, 0, sizeof(resp));
    if((ret = ump_send_msg(hndl, dev, SMCP1_GET_POSITIONS, 0, NULL, 0, NULL, 4, resp)) > 0)
    {
        positions->x = resp[0];
        if(ret > 1)
            positions->y = resp[1];
        if(ret > 2)
            positions->z = resp[2];
        if(ret > 3)
            positions->w = resp[3];
    }
    positions->updated_us = get_timestamp_us();
    return ret;
}

int ump_cu_select_manipulator(ump_state *hndl, const int dev)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(is_invalid_dev(dev))
        return set_last_error(hndl, LIBUMP_INVALID_DEV);
    return ump_cmd(hndl, SMCP1_ALL_CUS, SMCP1_CU_SET_SELECTED_MANIPULATOR, 1, &dev);
}

int ump_cu_set_speed_mode(ump_state *hndl, const int speed_mode, const int pen_step_size)
{
    int args[2];
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(is_invalid_speed_mode(speed_mode) || pen_step_size < 0)
        return set_last_error(hndl, LIBUMP_INVALID_ARG);
    args[0] = speed_mode;
    args[1] = pen_step_size;
    return ump_cmd(hndl, SMCP1_ALL_CUS, SMCP1_CU_SET_SPEED, 2, args);
}

int ump_cu_set_active(ump_state *hndl, const int active)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    return ump_cmd(hndl, SMCP1_ALL_CUS, SMCP1_CU_SET_ACTIVE, 1, &active);
}

int ump_cu_read_version(ump_state *hndl, int *version, const int size)
{
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(!version || size < 1)
        return set_last_error(hndl, LIBUMP_INVALID_ARG);
    return ump_send_msg(hndl, SMCP1_ALL_CUS, SMCP1_GET_VERSION, 0, NULL, 0, NULL, size, version);
}

int ump_get_device_list(ump_state *hndl, int *devs)
{
    // This is basically same as ump_get_broadcaster earlier, except terminology fixed due
    // device address found on the caches does not mean they necessarily broadcast
    // anything, address can be got e.g. from an ACK to a request.

    // libump errors are negative i.e. non-zero value, would had been interpreted as 'true'
    // Fixed and harmonized the return value. In the libump C-API let's use int systematically,
    // negative values indicating different kind of errors and leave boolean for C++.

    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);

    // Another difference is sending a ping request as a broadcast before
    // composing the list, this should update the address cache even if the device
    // is missing from the list e.g. due this function called soon after ump_open
    // and no position change notifications got yet
    int i, ret, found = 0;

    ump_cmd_options(hndl, SMCP1_OPT_REQ_ACK);
    // we may got LIBUMP_INVALID_DEV as return code due the broadcasted message is received
    // also by ourself and receiver id SMCP1_ALL_MANIPULATORS
    if((ret = ump_ping(hndl, SMCP1_ALL_MANIPULATORS)) < 0 &&
            ret != LIBUMP_INVALID_DEV && ret != LIBUMP_TIMEOUT)
        return ret;

    // above call returns when the first ACK is got to the ping
    // there may be more of they.
    if((ret = ump_receive(hndl, hndl->timeout)) < 0)
        return ret;

    for(i = 0; i < LIBUMP_MAX_MANIPULATORS; i++) {
        if(hndl->addresses[i].sin_family != 0)
            devs[found++] = i;        
    }
    return found;
}

int ump_clear_device_list(ump_state *hndl)
{
    int i, found = 0;
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    for (i = 0; i < LIBUMP_MAX_MANIPULATORS; i++) {
        if(hndl->addresses[i].sin_family != 0) {
            hndl->addresses[i].sin_family = 0;
            found++;
        }
    }
    return found;
}

int figure_cls_mode(const int step_x, const int step_y, const int step_z, const int step_w,
                            const int speed_x, const int speed_y, const int speed_z, const int speed_w)
{
    // CLS MODE SELECTION
    int smallest_speed = 1000;
    int cls_mode = 0;

    if ( step_x != 0 && speed_x > 0 && speed_x != SMCP1_ARG_UNDEF)
        smallest_speed = speed_x;
    if ( step_y != 0 && speed_y > 0 && speed_y != SMCP1_ARG_UNDEF && speed_y < smallest_speed )
        smallest_speed = speed_y;
    if ( step_z != 0 && speed_z > 0 && speed_z != SMCP1_ARG_UNDEF && speed_z < smallest_speed )
        smallest_speed = speed_z;
    if ( step_w != 0 && speed_w > 0 && speed_w != SMCP1_ARG_UNDEF && speed_w < smallest_speed)
        smallest_speed = speed_w;

    if (smallest_speed <= 50 && smallest_speed >= 10)
        cls_mode= 1; // CLS = 2
    else if (smallest_speed < 10)
        cls_mode= 2; // CLS = 1
    return cls_mode;
}

int umv_set_pressure(ump_state *hndl, const int dev, const int channel, const int value)
{
    int args[2];
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(channel < 1 || channel > 8 || value < 0 || value > 10000000)
        return set_last_error(hndl, LIBUMP_INVALID_ARG);
    args[0] = channel-1;
    args[1] = value;
    return ump_cmd(hndl, dev, SMCP1_UMV_SET_DAC, 2, args);
}

int umv_get_pressure(ump_state *hndl, const int dev, const int channel)
{
    int ret, resp[2], chn = channel-1;
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);

    if(channel < 1 || channel > 8)
        return set_last_error(hndl, LIBUMP_INVALID_ARG);

    if((ret = ump_send_msg(hndl, dev, SMCP1_UMV_GET_DAC, 1, &chn, 0, NULL, 2, resp)) < 0)
        return ret;
    if(resp[0] != chn || ret != 2)
        return set_last_error(hndl, LIBUMP_INVALID_RESP);
    return resp[1];
}

int umv_set_valve(ump_state *hndl, const int dev, const int channel, const int value)
{
    int args[2];
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);
    if(channel < 1 || channel > 8 || value < 0 || value > 1)
        return set_last_error(hndl, LIBUMP_INVALID_ARG);
    args[0] = channel-1;
    args[1] = value;
    return ump_cmd(hndl, dev, SMCP1_UMV_SET_DOX, 2, args);
}

int umv_get_valve(ump_state *hndl, const int dev, const int channel)
{
    int ret, resp[2], chn = channel-1;
    if(!hndl)
        return set_last_error(hndl, LIBUMP_NOT_OPEN);

    if(channel < 1 || channel > 8)
        return set_last_error(hndl, LIBUMP_INVALID_ARG);

    if((ret = ump_send_msg(hndl, dev, SMCP1_UMV_GET_DOX, 1, &chn, 0, NULL, 2, resp)) < 0)
        return ret;
    if(resp[0] != chn || ret != 2)
        return set_last_error(hndl, LIBUMP_INVALID_RESP);
    return resp[1];
}
