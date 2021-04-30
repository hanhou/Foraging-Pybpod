/*
 * A sample C-program for Sensapex micromanipulator SDK (umpsdk), remote TCU controls
 *
 * Copyright (c) 2016, Sensapex Oy
 * All rights reserved.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
 * EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 * OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 * IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
 * INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
 * BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
 * OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY
 * OF SUCH DAMAGE.
 *
 */

#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <sys/timeb.h>
#include "libump.h"

#define VERSION_STR   "v0.102"
#define COPYRIGHT "Copyright (c) Sensapex. All rights reserved"

#define DEV     1
#define UNDEF  (-1)
#define UPDATE  200

typedef struct params_s
{
    int verbose, wait, dev, speed, active, group;
    char *address;
} params_struct;

void usage(char **argv)
{
    fprintf(stderr,"usage: %s [opts]\n",argv[0]);
    fprintf(stderr,"TCU remote control options\n");
    fprintf(stderr,"-a\tactive\t0 for inactive mode, 1 for active\n");
    fprintf(stderr,"-d\tdev_id\tselect manipulator\n");
    fprintf(stderr,"-s\tspeed\tselect speed mode, 1 for snail, 6 for PEN\n");
    fprintf(stderr,"-v\tincrement verbose level\n");
    fprintf(stderr,"-w\tsecs\twait time before sending commands\n");
    fprintf(stderr,"-g\tgroup\tTCU group, default value 0 for group \'A\' on TCU UI\n");
    fprintf(stderr,"-A\taddress\tTCU unicast address (def: attempt to broadcast to %s)\n", LIBUMP_DEF_BCAST_ADDRESS);
    exit(1);
}

// Exits via usage() if an error occurs
void parse_args(int argc, char *argv[], params_struct *params)
{
    int i, v;
    memset(params, 0, sizeof(params_struct));
    params->active = UNDEF;
    params->address = LIBUMP_DEF_BCAST_ADDRESS;

    if(argc == 1)
        usage(argv);

    for(i = 1; i < argc; i++)
    {
        if(argv[i][0] == '-')
        {
            switch(argv[i][1])
            {
            case 'h': usage(argv);
            case 'v':
                params->verbose++;
                break;
            case 'q':
                params->verbose = 0;
                break;
            case 'a':
                if(i < argc-1 && sscanf(argv[++i],"%d",&v) == 1 && v >= 0)
                    params->active = v;
                else
                    usage(argv);
                break;
            case 'w':
                if(i < argc-1 && sscanf(argv[++i],"%d",&v) == 1 && v >= 0)
                    params->wait = v;
                else
                    usage(argv);
                break;
            case 'd':
                if(i < argc-1 && sscanf(argv[++i],"%d",&v) == 1 && v > 0)
                    params->dev = v;
                else
                    usage(argv);
                break;
            case 's':
                if(i < argc-1 && sscanf(argv[++i],"%d",&v) == 1 && v > 0)
                    params->speed = v;
                else
                    usage(argv);
                break;
            case 'g':
                if(i < argc-1 && sscanf(argv[++i],"%d",&v) == 1 && v > 0)
                    params->group = v;
                else
                    usage(argv);
                break;
            case 'A':
                if(i < argc-1 && argv[i+1][0] != '-')
                    params->address = argv[++i];
                else
                    usage(argv);
                break;
            default:
                usage(argv);
                break;
            }
        }
        else
            usage(argv);
    }
}

int main(int argc, char *argv[])
{
    ump_state *handle = NULL;
    int version[5], ret = 0;
    params_struct params;

    parse_args(argc, argv, &params);

    if((handle = ump_open(params.address, LIBUMP_DEF_TIMEOUT, params.group)) == NULL)
    {
        fprintf(stderr, "Open failed - %s\n", ump_last_errorstr(handle));
        exit(1);
    }

    if(params.verbose)
        ump_set_log_func(handle, params.verbose, NULL, NULL);

    ump_receive(handle, params.wait*1000+10);

    memset(version, 0, sizeof(version));
    if((ret = ump_cu_read_version(handle, version, 5)) > 0)
        printf("CU version %d.%d.%d.%d-%d\n", version[0], version[1], version[2], version[3], version[4]);
    else
        fprintf(stderr, "Read version failed - %s\n", ump_last_errorstr(handle));

    if(params.dev && (ret = ump_cu_select_manipulator(handle, params.dev)) < 0)
        fprintf(stderr, "Select dev failed - %s\n", ump_last_errorstr(handle));

    if(params.active != UNDEF && (ret = ump_cu_set_active(handle, params.active)) < 0)
        fprintf(stderr, "Set active failed - %s\n", ump_last_errorstr(handle));

    if(params.speed && (ret = ump_cu_set_speed_mode(handle, params.speed, 0)) < 0)
        fprintf(stderr, "Set speed mode failed - %s\n", ump_last_errorstr(handle));

    ump_close(handle);
    exit(ret < 0);
}
