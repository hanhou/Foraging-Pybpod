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

#define VERSION_STR   "TW-Jan-2017"

#define DEV	 1
#define UNDEF  (-1)
#define UPDATE  100
#define MOVE_AXIS_SIMULTANEOUSLY 1

typedef struct params_s{
	int x, i, s, update, dev;
	char *address;
} params_struct;

void usage(char **argv){
	fprintf(stderr,"usage: %s [opts]\n",argv[0]);
	fprintf(stderr,"Pptions\n");
	fprintf(stderr,"-d\tdev (def: %d)\n", DEV);
	fprintf(stderr,"Position change\n");
	fprintf(stderr,"-x\trelative target (um)\n");
	exit(1);
}

// Exits via usage() if an error occurs
void parse_args(int argc, char *argv[], params_struct *params){
	int i, v;
	float f;
	memset(params, 0, sizeof(params_struct));
	params->dev = DEV;
	params->update = UPDATE;
	params->address = LIBUMP_DEF_BCAST_ADDRESS;
	for(i = 1; i < argc; i++){
		if(argv[i][0] == '-'){
			switch(argv[i][1]){
			case 'h': usage(argv);
			case 'd':
				if(i < argc-1 && sscanf(argv[++i],"%d",&v) == 1 && v > 0)
					params->dev = v;
				else
					usage(argv);
				break;
			case 'x':
				if(i < argc-1 && sscanf(argv[++i],"%f",&f) == 1)
					params->x = (int)(f*1000.0);
				else
					usage(argv);
				break;
			case 'i':
				if(i < argc-1 && sscanf(argv[++i],"%d",&v) == 1)
					params->i = v*1000;
				else
					usage(argv);
				break;
			case 's':
				if(i < argc-1 && sscanf(argv[++i],"%d",&v) == 1)
					params->s = v;
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

static float um(const int nm){
	return (float)nm/1000.0;
}

int main(int argc, char *argv[]){
	ump_state *handle = NULL;
	int ret, status;
	int target_x,x,y,z;
	params_struct params;
	parse_args(argc, argv, &params);
	printf("Sensapex Descending SDK controller Jan 2017 TW\n");
	printf("BE VERY CAREFUL!!!!\n");
	if((handle = ump_open(params.address, LIBUMP_DEF_TIMEOUT, LIBUMP_DEF_GROUP)) == NULL){
		fprintf(stderr, "Open failed - %s\n", ump_last_errorstr(handle));
		exit(1);
	}
	if(ump_select_dev(handle, params.dev) <0){
		fprintf(stderr, "Device can't be selected (check name on manipulator) - %s\n", ump_last_errorstr(handle));
		ump_close(handle);
		exit(1);
	}
	if(ump_read_positions(handle) < 0){
		fprintf(stderr, "read positions failed - %s\n", ump_last_errorstr(handle));
		ump_close(handle);
		exit(1);
	}else{
		x = ump_get_x_position(handle);
		y = ump_get_y_position(handle);
		z = ump_get_z_position(handle);
		printf("Current position: %3.2f %3.2f %3.2f\n", um(x), um(y), um(z));
	}
	if(params.x){
		target_x = x + params.x;
		printf("Target position: %3.2f %3.2f %3.2f\n", um(target_x), um(y), um(z));
	}else{
		printf("No target set!");
		ump_close(handle);
		exit(3);
	}

	do{
		if((ret = ump_goto_position_ext(handle, params.dev, x+1000, y, z, 0, 1000, MOVE_AXIS_SIMULTANEOUSLY)) < 0){
			printf("Target movement: %3.2f %3.2f %3.2f\n", um(x+1000), um(y), um(z));
			fprintf(stderr, "Goto position failed - %s\n", ump_last_errorstr(handle));
			ump_close(handle);
			exit(6);
		}else{
			printf("Moved");
		}
		ret = ump_receive(handle, params.update);
		status = (int)ump_get_status(handle);
		do{
			if(status < 0){
				fprintf(stderr, "Status read failed - %s\n", ump_last_errorstr(handle));
				ump_close(handle);
				exit(1);
			}
			if(ump_read_positions(handle) < 0){
				fprintf(stderr, "read positions failed - %s\n", ump_last_errorstr(handle));
				ump_close(handle);
				exit(1);
			}else{
				x = ump_get_x_position(handle);
				//y = ump_get_y_position(handle);
				//z = ump_get_z_position(handle);
				printf("Current position: %3.2f %3.2f %3.2f\n", um(x), um(ump_get_y_position(handle)), um(ump_get_z_position(handle)));
			}
			ump_receive(handle, params.update);
			status = ump_get_status(handle);
		}while(ump_is_busy_status(status));
		Sleep(500);
	}while(x < target_x);
	ump_close(handle);
	exit(!ret);
}
