/**
 *
 * Sensapex microManipulator Control Protocol v1 definitions
 * Public SDK version.
 *
 * Copyright (c) 2015-2019 Sensapex. All rights reserved
 *
 * The Sensapex micromanipulator SDK is free software: you can redistribute
 * it and/or modify it under the terms of the GNU Lesser General Public License
 * as published by the Free Software Foundation, either version 3 of the License,
 * or (at your option) any later version.
 *
 * The Sensapex Micromanipulator SDK is distributed in the hope that it will be
 * useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with the Sensapex micromanipulator SDK. If not, see
 * <http://www.gnu.org/licenses/>.
 *
 */

#ifndef LIBUMP_SMCP1_H
#define LIBUMP_SMCP1_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SMCP1_BCAST_ADDR      "169.254.255.255"

#define SMCP1_VERSION          0x10
#define SMCP1_ARG_UNDEF        INT32_MAX

#define SMCP1_ALL_MANIPULATORS 0x00ff
#define SMCP1_ALL_CUS          0x01ff
#define SMCP1_ALL_PCS          0x02ff
#define SMCP1_ALL_CUS_OR_PCS   (SMCP1_ALL_CUS|SMCP1_ALL_PCS)
#define SMCP1_ALL_OTHERS       0x04ff
#define SMCP1_ALL              0xffff

#define SMCP1_DEF_UDP_PORT     55555

typedef enum
{
    // Basic data types 0 - 9
    SMCP1_DATA_VOID                 = 0,
    SMCP1_DATA_UINT8                = 1,
    SMCP1_DATA_INT8                 = 2,
    SMCP1_DATA_UINT16               = 3,
    SMCP1_DATA_INT16                = 4,
    SMCP1_DATA_UINT32               = 5,
    SMCP1_DATA_INT32                = 6,
    SMCP1_DATA_UINT64               = 7,
    SMCP1_DATA_INT64                = 8,
    // Array of UTF8 encoded 16bit unicode chars (NOTE: 8bit US ASCII is a legal subset, latin1 is NOT).
    // May contain terminating zero or zero padding to 32 bit boundary (but neither one required).
    SMCP1_DATA_CHAR_STRING          = 9,

} smcp1_data_type;

typedef enum
{
    // May be used for pinging manipulator (just request RESP and/or ACK)
    // Arguments: any. Response is whole request (to carry timestamp etc)
    SMCP1_CMD_PING                     = 0,
    // Emergency stop, no arguments
    SMCP1_CMD_STOP                     = 1,
    // Warning before switching supply power off, no arguments
    SMCP1_CMD_SLEEP                    = 2,
    // would be needed, no arguments
    SMCP1_CMD_REBOOT                   = 3,
    // Initialize zero position drive
    SMCP1_CMD_INIT_ZERO                = 4,
    // End user accessible (voltage) calibration
    // argument: calibration type
    SMCP1_CMD_CALIBRATE                = 5,

    // End user accessible friction stabilization,
    // simplified and safer version of related production command
    // argument: loop count (e.g. in range of 20-200).
    SMCP1_CMD_DRIVE_LOOP               = 6,

    // Enable/disable PEN mode, VZ, tracking etc
    // Arguments: feature number 0-63, value 0 or 1, no response
    SMCP1_SET_FEATURE                  = 11,
    // Get state of a single feature
    // Argument: feature number 0-63
    // Response: feature number 0-63, value 0 or 1
    SMCP1_GET_FEATURE                  = 12,
    // Get state of all features as a bitmask
    // Arguments: none, response UINT64
    SMCP1_GET_FEATURES                 = 13,

    // Get positions syncronically
    // Arguments: none
    // Response: array of 1, 3 or 4 INT32 positions - same as position notification
    SMCP1_GET_POSITIONS                = 14,

    // Set user accessible parameter, similar to current register write, but production/service
    // parameters via different command, to be seen what will remain when e.g. memory drive
    // speed will command argument
    // Arguments: parameter id, value
    SMCP1_SET_PARAMETER                = 15,

    // Argument: parameter id
    // Response: parameter id, value
    SMCP1_GET_PARAMETER                = 16,

    SMCP1_SET_EXT_FEATURE              = 17,
    // Get state of a single beta feature
    // Argument: feature number 32-63
    // Response: feature number 32-63, value 0 or 1
    SMCP1_GET_EXT_FEATURE              = 18,
    // Get state of all beta features as a bitmask
    // Arguments: none, response UINT32
    SMCP1_GET_EXT_FEATURES             = 19,

    // Argument: LED id 0-2, value 0 or 1
    SMCP1_SET_LED                      = 21,
    // Argument: LED ID
    // Reponse: LED ID, value 0 or 1
    SMCP1_GET_LED                      = 22,

    // Argument: none
    // Response: array of UINT32s, proposed format contains 3 or parts X.Y.Z (or X.Y.Z-W),
    // -w intented for different default parametrization with same source files.
    // First commercial release version to be 1.0.0-1, a bug fix to it 1.0.2-1,
    // A small new feature or functionality improvement 1.1.0-1.
    // New feature 1.2.0-1
    // New generation 2.0.0-1 - typically requiring all devices to on the system to be upgraded to same level
    SMCP1_GET_VERSION                 = 23,

    // Argument: none
    // Response: SMCP1_DATA_CHAR_STRING containing human readable, non localized, text string
    SMCP1_GET_INFO_TEXT               = 24,

    // store current position to a certain storage index
    // Argument: storage index 1-99, home = 1 / target = 2, no response
    SMCP1_CMD_STORE_MEM                = 31,

    // drive to stored position via storage index
    // Arguments: storage index 1-99, home = 1 / target = 2,
    //            speed in um/s
    //            axis drive mode (optional), 0 (def) = one-by-one, 1 = simultaneusly,
    //            max acceleration in um/s^2 (optional, requires axis drive mode),
    // no response
    // Notification: status code, positions, completed/failed
    SMCP1_CMD_GOTO_MEM                 = 32,

    // drive to certain position (non-defined axis not moved)
    // Arguments: positions (1, 3 or 4 pcs, populate SMCP1_ARG_UNDEF for non-affected ones),
    //            speed in um/s (optional, 4 position required),
    //            axis drive mode (optional), 0 (def) = one-by-one like in memory pos drive, 1 = all axis simultaneusly,
    //            max acceleration in um/s^ 2 (optional, 4 positions, speed and drive mode required),

    // Alternatively axis specific speeds may be inserted into the second subblock

    // no response
    // Notification: status code, positions (1,3 or 4 pcs)
    SMCP1_CMD_GOTO_POS                 = 33,

    // Take x nm (INT32) step from current pos
    // Arguments: nm (INT32) steps, array of 1, 3 or 4 values, zero step for axis not to be moved X, [Y, Z[, W]],
    //            speeds um/s for every axis (optional, requires 4 steps),
    //            max acceleration (requires 4 steps and 4 speeds)
    // Positive step for forward and negative for backward movement.
    // Speed or acceleration always positive.
    SMCP1_CMD_TAKE_STEP                = 34,

    // Legacy open loop manual movement control.
    // Arguments: speed mode (1 = SNAIL, 6 = PEN)
    // relative speeds 0-100 in INT32, 0 for axis not to be moved
    // array of 1, 3 or 4 relative speed values 0-100, X, [Y, Z[, W]]
    // Positive values for forward and negative for backward.
    // TODO get rid of this, better sooner than later
    SMCP1_CMD_TAKE_LEGACY_STEP         = 35,

    // Read acceleration sensor values.
    // Arguments: none
    // Response: array of 3x1, 3x3 or 3x4 INT32 values, for 1, 3 or 4 axis models respectively.
    // Each number should be right justified (i.e. resolution 1bit) signed value combining
    // OUT_x_MSB and OUT_x_LSB for every acceleration sensor axis X,Y and Z.
    SMCP1_CMD_GET_ACCELERATIONS        = 36,

    // E.g. after error status notification is been got, no arguments
    // Response error state UINT32
    SMCP1_READ_ERROR_STATE             = 41,
    // Clear error state, no arguments, no response
    SMCP1_CLEAR_ERROR_STATE            = 42,

    SMCP1_CMD_TAKE_JACKHAMMER_STEP     = 43,

    SMCP1_CMD_GET_AXIS_ANGLE           = 44,

	// Move in virtual axis
	// Arguments:
	//  - The target position of X actuator (nm)
	//  - The drive speed of X actuator (um/s)
	// Response:
	//  - None
	SMCP1_CMD_GOTO_VIRTUAL_AXIS_POSITION = 45,

 // Activate an additional feature
    // Arguments:
    //  - Feature ID
    //  - on / off
    //  - activation secret (8 * uin32_t)
    SMCP1_CMD_SET_FEATURE_MASK            = 46,


    // Get the activation status of an additional feature
    // Arguments:
    //  - Feature ID
    // Response:
    //  - ON (1)/OFF(0)
    SMCP1_CMD_GET_FEATURE_MASK            = 47,

    // Get activation statuses of all additional features
    SMCP1_CMD_GET_FEATURES_MASK           = 48,

    // Convenience API for checking a feature's functional status
    // Combines SMCP1_CMD_GET_FEATURE_MASK and SMCP1_GET_FEATURES
    //
    // Arguments:
    //  - Feature ID
    // Response:
    //  - 1 == A feature is functional (enabled and activated)
    //  - 0 == A feature is not functional (disabled or/and not activated)
    SMCP1_CMD_GET_FEATURE_FUNCTIONALITY   = 49,


    // umv2018 special commands
    // Set pressure control voltage DAC
    // Arguments: channel 0-7, value (TODO define scaling and thus value range e.g. 0 - 10000mV or pressure?)
    SMCP1_UMV_SET_DAC                         = 90,
    // Get current pressure control voltage DAC value
    // Argument: channel 0-7
    // Response: channe, value
    SMCP1_UMV_GET_DAC                         = 91,

    // Enable disable valve control digital output
    // Arguments: channel 0-7, value 0 or 1, no response
    SMCP1_UMV_SET_DOX                         = 92,
    // Get state of valve control digital output
    // Argument: channel 0-7
    // Response: channel, value 0 or 1
    SMCP1_UMV_GET_DOX                         = 93,


    // Notifications from manipulator

    // Notification arguments: none
    // smcp1 frame with type =  SMCP1_CMD_MANIPULATOR_HELLO, sub_blocks = 0, no ACK request
    SMCP1_NOTIFY_MANIPULATOR_HELLO        = 100, // for manipulator address/dev id mapping

    // Notification arguments: array of 1, 3 or 4 INT32 positions
    SMCP1_NOTIFY_POSITION_CHANGED         = 101,

    // Notification arguments: UINT32 (or UINT64 if run out of bits)
    SMCP1_NOTIFY_STATUS_CHANGED           = 102, // like moving or stuck

    // Notification argument: UINT32 error code (i.e. zero for ok)
    SMCP1_NOTIFY_GOTO_ZERO_COMPLETED      = 103,

    // Notification argument: UINT32 error code (i.e. zero for ok)
    SMCP1_NOTIFY_GOTO_POS_COMPLETED       = 104,

    // Notification argument: UINT32 error code (i.e. zero for ok)
    SMCP1_NOTIFY_CALIBRATE_COMPLETED      = 121,

    // Notification argument: UINT32 error code (i.e. zero for ok)
    SMCP1_NOTIFY_DRIVE_LOOP_COMPLETED     = 122,


    // Commands for TCU remote control
    SMCP1_CU_SET_SELECTED_MANIPULATOR     = 203,
    SMCP1_CU_SET_SPEED                    = 205,
    SMCP1_CU_SET_ACTIVE                   = 207,

        // Commands from SDK to TCU remote control
    // SMCP1_CU_ENABLE_MANIPULATORS      = 201, not needed/usable currently
    // Get commands not supported yet

    SMCP1_CU_GET_SELECTED_MANIPULATOR    = 204,
    SMCP1_CU_GET_SPEED                   = 206,
    SMCP1_CU_GET_ACTIVE                  = 208,

    // SDK can query firmware versions of the RWx(s) connected to the TCU.
    // Argument: RWx unit number, omit argument, value 0 or 1 for the first
    // and value 2 for the second one.
    // Response: 4 UINT32, similar version number scheme as for MCU, see
    // SMCP1_GET_VERSION comments above

    SMCP1_CU_GET_RWX_FW_VERSION           = 210,

    // Arguments: feature number 0-63, value 0 or 1, no response
    SMCP1_RD_SET_FEATURE                  = 501,
    // Get state of a single feature
    // Argument: feature number 0-63
    // Response: feature number 0-63, value 0 or 1
    SMCP1_RD_GET_FEATURE                  = 502,
    // Get state of all features as a bitmask
    // Arguments: none, response UINT64
    SMCP1_RD_GET_FEATURES                 = 503,

    // RD notifiations shall not be enabled by default and may not be included in a release build.
    // Traces over IP, obsoletes any need for special trace tools - except for debuggin the UDP/IP/ethernet layers
    // Notification argument: SMCP1_DATA_CHAR_STRING
    SMCP1_RD_NOTIFY_TRACE_TEXT            = 601,
    // Some production test messages
    SMCP1_RD_NOTIFY_PIEZO_INFO            = 602,
    SMCP1_CMD_PROD_FIRMWARE_UPLOAD        = 1111,

} smcp1_cmd;

/**
  * Parameters, these were register values in legacy models
  *
  */

typedef enum {
    SMCP1_PARAM_SPEED                   = 1,
    SMCP1_PARAM_MEM_SPEED               = 2,
    SMCP1_PARAM_DEV_ID                  = 3,
    SMCP1_PARAM_VIRTUALX_ANGLE          = 4, // angle value degrees*10

    // Readonly via SDK
    SMCP1_PARAM_HW_ID                   = 0x101,
    SMCP1_PARAM_SN                      = 0x102,
    SMCP1_PARAM_EOW                     = 0x103,

    SMCP1_PARAM_VIRTUALX_DETECTED_ANGLE = 0x104, // calculated from X-axis acceleration sensor data
    SMCP1_PARAM_AXIS_COUNT              = 0x105,
    SMCP1_PARAM_ETHERNET_MAC            = 0x106,

    SMCP1_PARAM_ACT0_PIEZO_INFO           = 0x120,
    SMCP1_PARAM_ACT1_PIEZO_INFO           = 0x121,
    SMCP1_PARAM_ACT2_PIEZO_INFO           = 0x122,
    SMCP1_PARAM_ACT3_PIEZO_INFO           = 0x123,
} smcp1_params;

typedef enum {
    SMCP10_FEAT_VIRTUAL_AXIS            = 0x0,  // Bit 0
    SMCP10_FEAT_INVERT_VIRTUAL_AXIS     = 0x1,  // Bit 1
    SMCP10_FEAT_TRANSITION_LIMITS       = 0x2,  // Bit 2
    SMCP10_FEAT_W_AS_VIRTUAL_AXIS       = 0x3,  // Bit 3
    SMCP10_FEAT_PREVENT_MOVEMENT        = 0x4   // Bit 4
} smcp1_features;

/**
 * Note: keep inline with 32bit boundaries - othervice message needs to be
 * composed and parsed byte by byte.

   0                                                     bit 31
   +--------------+-----------+------------------------------+
0  | version 0x10 | extra     |     receiver id              | 0-3
   +--------------+-----------+------------------------------+
32 |           sender id      |     message id               | 3-7
   +--------------------------+------------------------------+
64 |                       parameters                        | 8-11
   +--------------------------+------------------------------+
96 |           type           |     sub_blocks = 1           | 12-15 (e.g.)
   +--------------------------+------------------------------+
128|        sb_type = 2       |     sb_size =  1             | 16-20 (e.g.)
   +--------------------------+---------------+--------------+
160| Right justified to boundary, zero padding|   INT8       | 20-24 (e.g.)
   +------------------------------------------+--------------+
*/

typedef struct
{
    // 0 (byte index in the receive buffer)
    uint8_t  version;       // Protocol version, for smcpv1 == 0x10, smcpv0 version was 0x02
    // 1
    uint8_t  extra;         // Reserved for future usage
    // 2-3
    uint16_t receiver_id;   // ID of message receiver (1, 2, 3 ... , 255 to multicast to all manipulators with id < 255)
    // 4-5
    uint16_t sender_id;     // ID of message sender (CUBa's Id > 0x100, PC's Id > 0x200, values above 0x1000 reserved for future)
    // 6-7
    uint16_t message_id;    // Message ID (autoincremented counter)
    // 8-11
    uint32_t options;       // Bitmask i.e. message is a response or request an ACK when operation is completed
    // 12-13
    uint16_t type;          // Message type/command
    // 14-15
    uint16_t sub_blocks;    // The total count of the following sub block(s), zero for command without arguments
    // 0-N sub blocks to follow on wire
} smcp1_frame;

#define SMCP1_FRAME_SIZE   sizeof(smcp1_frame)

typedef struct
{
    uint16_t data_type;
    uint16_t data_size; // number of objects in the array
} smcp1_subblock_header;

#define SMCP1_SUB_BLOCK_HEADER_SIZE   sizeof(smcp1_subblock_header)

/**
 * ACK is sent (if requested) when message received and understood (but not processed, ACK is used only for transport error detection)
 *     error bit set if an unicast message was received, but can not be parsed.
 * ACK contains always only the smcp1 frame header, not the arguments often carried by the request
 * RESP is a response for the request e.g. when reading parameter value, also response may request an ACK
 * NOTIFY is sent (if requested) when operation like zero position drive or calibration completed or failed, may request an ACK
 */

#define SMCP1_OPT_PRIORITY     0x00000100  // 0 = normal message

#define SMCP1_OPT_WAIT_TRIGGER_1    0x00000200  // Set command to executed after trigger in line 2 activates
#define SMCP1_OPT_PRIORITY          0x00000100  // 0 = normal message

// send ACK, RESP or NOTIFY to the bcast address (combine with REQs below), 0 = unicast to the sender
#define SMCP1_OPT_REQ_BCAST    0x00000080

// request notification (e.g. on completed memory drive), 0 = do not notify
#define SMCP1_OPT_REQ_NOTIFY   0x00000040
#define SMCP1_OPT_REQ_RESP     0x00000020  // request RESP, 0 = no RESP requested
#define SMCP1_OPT_REQ_ACK      0x00000010  // request ACK, 0 = no ACK requested

// Set if frame indicates an error (combine with NOTIFY, RESP or ACK, to be ignored on request)
#define SMCP1_OPT_ERROR        0x00000008

#define SMCP1_OPT_NOTIFY       0x00000004  // frame is a notification, 0 = not notification
#define SMCP1_OPT_ACK          0x00000002  // frame is an ACK, 0 = not an ACK
#define SMCP1_OPT_REQ          0x00000001  // frame is a request, 0 = frame is a response

// status bitmask
#define SMCP1_STATUS_IDLE      0x00000000

#define SMCP1_STATUS_X_MOVING  0x00000010
#define SMCP1_STATUS_Y_MOVING  0x00000020
#define SMCP1_STATUS_Z_MOVING  0x00000040
#define SMCP1_STATUS_W_MOVING  0x00000080

#define SMCP1_STATUS_BUSY      0x00000001  // processing (not necessarily moving)
#define SMCP1_STATUS_ERROR     0x00000008  // error state

#ifdef __cplusplus
}
#endif

#endif // SMCP1_H


