/*
 * A sample C-program for Sensapex micromanipulator SDK (umpsdk)
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

#define VERSION_STR   "v0.111"
#define COPYRIGHT "Copyright (c) Sensapex. All rights reserved"

#define DEV     1
#define UNDEF  (-1)
#define UPDATE  200

typedef struct params_s
{
    int x, y, z, w, X, Y, Z, W;
    int verbose, update, loop, dev, speed;
    char *address;
} params_struct;

void usage(char **argv)
{
    fprintf(stderr,"usage: %s [opts]\n",argv[0]);
    fprintf(stderr,"Generic options\n");
    fprintf(stderr,"-d\tdev (def: %d)\n", DEV);
    fprintf(stderr,"-v\tverbose\n");
    fprintf(stderr,"-a\taddress (def: %s)\n", LIBUMP_DEF_BCAST_ADDRESS);
    fprintf(stderr,"Position change\n");
    fprintf(stderr,"-x\trelative target (um, decimal value accepted)\n");
    fprintf(stderr,"-y\trelative target \n");
    fprintf(stderr,"-z\trelative target \n");
    fprintf(stderr,"-w\trelative target \n");
    fprintf(stderr,"-X\tabs target (um, decimal value accepted\n");
    fprintf(stderr,"-Y\tabs target \n");
    fprintf(stderr,"-Z\tabs target \n");
    fprintf(stderr,"-W\tabs target \n");
    fprintf(stderr,"-n\tcount\tloop current and target positions \n");
    exit(1);
}

// Exits via usage() if an error occurs
void parse_args(int argc, char *argv[], params_struct *params)
{
    int i, v;
    float f;
    memset(params, 0, sizeof(params_struct));
    params->X = UNDEF;
    params->Y = UNDEF;
    params->Z = UNDEF;
    params->W = UNDEF;
    params->dev = DEV;
    params->update = UPDATE;
    params->address = LIBUMP_DEF_BCAST_ADDRESS;
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
            case '1':
                params->verbose = 0;
                break;
            case 'n':
                if(i < argc-1 && sscanf(argv[++i],"%d",&v) == 1 && v > 0)
                    params->loop = v;
                else
                    usage(argv);
                break;
            case 'u':
                if(i < argc-1 && sscanf(argv[++i],"%d",&v) == 1 && v > 0)
                    params->update = v;
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
            case 'x':
                if(i < argc-1 && sscanf(argv[++i],"%f",&f) == 1)
                    params->x = (int)(f*1000.0);
                else
                    usage(argv);
                break;
            case 'y':
                if(i < argc-1 && sscanf(argv[++i],"%f",&f) == 1)
                    params->y = (int)(f*1000.0);
                else
                    usage(argv);
                break;
            case 'z':
                if(i < argc-1 && sscanf(argv[++i],"%f",&f) == 1)
                    params->z = (int)(f*1000.0);
                else
                    usage(argv);
                break;
            case 'w':
                if(i < argc-1 && sscanf(argv[++i],"%f",&f) == 1)
                    params->w = (int)(f*1000.0);
                else
                    usage(argv);
                break;
            case 'X':
                if(i < argc-1 && sscanf(argv[++i],"%f",&f) == 1 && f >= 0)
                    params->X = (int)(f*1000.0);
                else
                    usage(argv);
                break;
            case 'Y':
                if(i < argc-1 && sscanf(argv[++i],"%f",&f) == 1 && f >= 0)
                    params->Y = (int)(f*1000.0);
                else
                    usage(argv);
                break;
            case 'Z':
                if(i < argc-1 && sscanf(argv[++i],"%f",&f) == 1 && f >= 0)
                    params->Z = (int)(f*1000.0);
                else
                    usage(argv);
                break;
            case 'W':
                if(i < argc-1 && sscanf(argv[++i],"%f",&f) == 1 && f >= 0)
                    params->W = (int)(f*1000.0);
                else
                    usage(argv);
                break;
            case 'a':
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

static float um(const int nm)
{
    return (float)nm/1000.0;
}


int main(int argc, char *argv[])
{
    ump_state *handle = NULL;
    int ret, status, loop = 0;
    int target_x = 0, target_y = 0, target_z = 0, target_w = 0;
    int home_x = 0, home_y = 0, home_z = 0, home_w = 0;
    params_struct params;

    parse_args(argc, argv, &params);

    if((handle = ump_open(params.address, LIBUMP_DEF_TIMEOUT, LIBUMP_DEF_GROUP)) == NULL)
    {
        // Feeding NULL handle is intentional, it obtains the
        // last OS error which prevented the port to be opened
        fprintf(stderr, "Open failed - %s\n", ump_last_errorstr(handle));
        exit(1);
    }

    if(ump_select_dev(handle, params.dev) <0)
    {
        fprintf(stderr, "Select dev failed - %s\n", ump_last_errorstr(handle));
        ump_close(handle);
        exit(2);
    }

    printf("Axis count %d\n", ump_get_axis_count(handle, params.dev));

    /*
     * These functions providing the axis position as return value
     * are convenient e.g. for mathlab usage.
     * For C code use ump_get_positions(handle,&x,&y,&z,&w)
     *
     * First read the position from the manipulator (or check that cache contains valid values)
     */

    if(ump_read_positions(handle) < 0)
    {
        fprintf(stderr, "read positions failed - %s\n", ump_last_errorstr(handle));
        home_x = home_y = home_z = home_w = 0;
    }
    else // next obtain the position values
    {
        home_x = ump_get_x_position(handle);
        home_y = ump_get_y_position(handle);
        home_z = ump_get_z_position(handle);
        home_w = ump_get_w_position(handle);
    }

    printf("Current position: %3.2f %3.2f %3.2f %3.2f\n", um(home_x), um(home_y), um(home_z), um(home_w));

    // Calculate target positions, relative
    if(params.x)
        target_x = home_x + params.x;
    if(params.y)
        target_y = home_y + params.y;
    if(params.z)
        target_z = home_z + params.z;
    if(params.w)
        target_w = home_w + params.w;
    // or absolutely
    if(params.X != UNDEF)
        target_x = params.X;
    if(params.Y != UNDEF)
        target_y = params.Y;
    if(params.Z != UNDEF)
        target_z = params.Z;
    if(params.W != UNDEF)
        target_w = params.W;

    do
    {
        int x, y, z, w;
        if(loop&1)
            x = home_x, y = home_y, z = home_z, w = home_w;
        else
            x = target_x, y = target_y, z = target_z, w = target_w;
        if(params.loop)
            printf("Target position: %3.2f %3.2f %3.2f %3.2f (%d/%d)\n", um(x), um(y), um(z), um(w), loop+1, params.loop);
        else
            printf("Target position: %3.2f %3.2f %3.2f %3.2f\n", um(x), um(y), um(z), um(w));

        if((ret = ump_goto_position(handle, x, y, z, w, params.speed)) < 0)
        {
            fprintf(stderr, "Goto position failed - %s\n", ump_last_errorstr(handle));
            continue;
        }
        if(!params.loop && !params.verbose)
            break;
        ret = ump_receive(handle, params.update);
        status = (int)ump_get_status(handle);
        while(ump_is_busy_status(status))
        {
            if(params.verbose)
            {
                if(status < 0)
                    fprintf(stderr, "Status read failed - %s\n", ump_last_errorstr(handle));
                else if(ump_get_positions(handle, &x, &y, &z, &w) < 0)
                    fprintf(stderr, "Get positions failed - %s\n", ump_last_errorstr(handle));
                else
                    printf("%3.2f %3.2f %3.2f %3.2f status %02X\n", um(x), um(y), um(z), um(w), status);
            }
            ump_receive(handle, params.update);
            status = ump_get_status(handle);
       }
	} while(++loop < params.loop);
    ump_close(handle);
    exit(!ret);
}
