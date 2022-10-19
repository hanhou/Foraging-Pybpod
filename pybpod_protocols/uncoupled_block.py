'''
Generate uncoupled block reward schedule
(by on-line updating)

adapted from Cohen lab's Arduino code
'''

import numpy as np
import matplotlib.pyplot as plt

def generate_first_block():
    pass
  
def generate_next_block():
    pass
  

choices = {'L', 'R'}
reward_probs = [0.1, 0.5, 0.9]
block_min = 20
block_max = 35
block_stagger = (round(block_max - block_min - 0.5) / 2 + block_min) / 2
total_trial = 1000

perseve_add = True
perseverative_limit = 4

block_index_L = 0
block_index_R = 0
trial_now = 0

generate_first_block()

while trial_now <= total_trial:
    '''
    run protocol here
    '''    
    
    trial_now += 1
  
  





Serial.println();
task.generateFirstBlock(block_min, block_max, blockArray, block_index_L, block_index_R, block_stagger);
}



void loop() {
if (running == false){
  task.lickDetect();
  task.deliverManualWater();
  task.manualStartAndPause(running);
  task.clearSerialCache();
} else if (running == true) {
  if ((task.CSplusTrialNumber > task.blockSwitchL[blockIndexL])){
    blockIndexL++; 
    Serial.println();
    task.generateNextBlockL(block_min, block_max, blockArray, blockIndexL, blockIndexR, blockStagger);
  }
  if ((task.CSplusTrialNumber > task.blockSwitchR[blockIndexR])){
    blockIndexR++; 
    Serial.println();
    task.generateNextBlockR(block_min, block_max, blockArray, blockIndexL, blockIndexR, blockStagger);
    if ((task.CSplusTrialNumber > task.blockSwitchL[blockIndexL])){
      blockIndexL++; 
      Serial.println();
      task.generateNextBlockL(block_min, block_max, blockArray, blockIndexL, blockIndexR, blockStagger);
    }
  }


  trialNumber++;
  
  if (CSplusFlag) { // if previous trial was CSplus
    if (task.anyLick_L || task.anyLick_R){
      task.CSplusTrialNumber++; // iterate CS+ trial
    }
    if (persevAdd){
      autoShapePerseverance();
    }
    if (autoPauseFlag){
      autoPause();
    }
  }
  task.manualStartAndPause(running);
//    changeVariables();
  task.clearSerialCache();


  if (!running){
    task.releaseSolenoid();
    Serial.print("Total L Reward: "); Serial.print(task.totalRewardL); 
    Serial.print(" / Total R Reward: "); Serial.println(task.totalRewardR);
    Serial.print("Total Reward Volume: "); Serial.println((task.totalRewardL + task.totalRewardR)*waterVolume);
    if (persevAdd) {
      Serial.print("PersevAdd: "); Serial.println(numPersevAdd);
    }
    if (autoPauseFlag){
      Serial.print("Auto Pauses: "); Serial.println(numAutoPauses);
    }
  }
}
}


void taskSettings::generateFirstBlock(int block_min, int block_max, int blockArray[], int blockIndexL, int blockIndexR, int blockStagger, int sizeOfArray){
  Serial.println("Enter L Port Probability");
  while(Serial.available() == 0);{
      if (Serial.peek() == 'r'){
          randomBlockProbs = true;
      }else{
          waterContingency_L[0] =  Serial.parseInt();
          Serial.println(waterContingency_L[0]);
          Serial.println("Enter R Port Probability");
          taskSettings::clearSerialCache();
          waterContingency_R[0] = Serial.parseInt();
          Serial.println(waterContingency_R[0]);
      }
  }
  if (random(2) == 1){
      taskSettings::generateNextBlockL(block_min, block_max, blockArray, blockIndexL, blockIndexR, blockStagger, sizeOfArray);
      delay(5);
      taskSettings::generateNextBlockR(block_min, block_max, blockArray, blockIndexL, blockIndexR, blockStagger, sizeOfArray);
  }else{
      taskSettings::generateNextBlockR(block_min, block_max, blockArray, blockIndexL, blockIndexR, blockStagger, sizeOfArray);
      delay(5);
      taskSettings::generateNextBlockL(block_min, block_max, blockArray, blockIndexL, blockIndexR, blockStagger, sizeOfArray);
  }
  if (waterContingency_L[0] <= waterContingency_R[0]){
      blockSwitchL[blockIndexL] = blockSwitchL[blockIndexL] - blockStagger;  
  }else{
      blockSwitchR[blockIndexR] = blockSwitchR[blockIndexR] - blockStagger; 
}
}


void taskSettings::generateNextBlockL(int block_min, int block_max, int blockArray[], int blockIndexL, int blockIndexR, int blockStagger, int sizeOfArray){
  // generate new block 1 at a time; allows for flexibility in changing block_min/block_max
  if (blockIndexL == 0){
      blockSwitchL[blockIndexL] = random(block_max - block_min + 1) + block_min; // init first as rand
      if (randomBlockProbs == true){
          tempProbInd = random(sizeOfArray);
          waterContingency_L[0] = blockArray[tempProbInd];
          while (waterContingency_L[blockIndexL] == 10 && waterContingency_R[blockIndexR] == 10){
              tempProbInd = random(sizeOfArray);
              waterContingency_R[blockIndexR] = blockArray[tempProbInd];
          }
      }
  } else {
      blockSwitchL[blockIndexL] = random(block_max - block_min + 1) + block_min + blockSwitchL[blockIndexL-1];
      if (blockIndexL > 0){
          if (waterContingency_L[blockIndexL - 1] > waterContingency_R[blockIndexR]){
              rwdContingencyTallyL++;
              rwdContingencyTallyR = 0;
          }else if (waterContingency_L[blockIndexL - 1] == waterContingency_R[blockIndexR]){
              rwdContingencyTallyL++;
              rwdContingencyTallyR++;
          }else{
              rwdContingencyTallyL = 0;
              rwdContingencyTallyR++;
          }
      }
      if (rwdContingencyTallyL > 3){
          waterContingency_L[blockIndexL] = 10;
          rwdContingencyTallyL = 0;
          rwdContingencyTallyR = 0;
          Serial.println("**************forced L probability contingency***************");
      } else {
          tempProbInd = random(sizeOfArray);
          waterContingency_L[blockIndexL] = blockArray[tempProbInd];
      }
      while (waterContingency_L[blockIndexL] == waterContingency_L[blockIndexL-1]){
          tempProbInd = random(sizeOfArray);
          waterContingency_L[blockIndexL] = blockArray[tempProbInd];
      }
      if (waterContingency_L[blockIndexL] == 10 && waterContingency_R[blockIndexR] == 10){ 		//pushes previous 10 port to a higher prob to keep one port from maintaining the higher prob
        blockSwitchL[blockIndexL] = blockSwitchL[blockIndexL] - blockStagger;                  //to keep blocks staggered when they both start new ones
        blockSwitchR[blockIndexR] = CSplusTrialNumber - 1;
        blockIndexR++;
      }
  }
  Serial.print("L Block Switch at Trial "); Serial.print(blockSwitchL[blockIndexL]);
  Serial.print(". Rewards (L/R) = "); Serial.print(waterContingency_L[blockIndexL]);
  Serial.print("/"); Serial.println(waterContingency_R[blockIndexR]);
}

void taskSettings::generateNextBlockR(int block_min, int block_max, int blockArray[], int blockIndexL, int blockIndexR, int blockStagger, int sizeOfArray){
  // generate new block 1 at a time; allows for flexibility in changing block_min/block_max
  if (blockIndexR == 0){
      blockSwitchR[blockIndexR] = random(block_max - block_min + 1) + block_min; // init first as rand
      if (randomBlockProbs == true){
          tempProbInd = random(sizeOfArray);
          waterContingency_R[0] = blockArray[tempProbInd];
          while (waterContingency_L[blockIndexL] == 10 && waterContingency_R[blockIndexR] == 10){
              tempProbInd = random(sizeOfArray);
              waterContingency_R[blockIndexR] = blockArray[tempProbInd];
          }
      }    
  } else {
      blockSwitchR[blockIndexR] = random(block_max - block_min + 1) + block_min + blockSwitchR[blockIndexR-1];
      if (blockIndexR > 0){
          if (waterContingency_R[blockIndexR - 1] > waterContingency_L[blockIndexL]){
              rwdContingencyTallyR++;
              rwdContingencyTallyL = 0;
          }else if (waterContingency_R[blockIndexR - 1] == waterContingency_L[blockIndexL]){
              rwdContingencyTallyR++;
              rwdContingencyTallyL++;
          }else{
              rwdContingencyTallyR = 0;
              rwdContingencyTallyL++;
          }
      }
      if (rwdContingencyTallyR > 3){
          waterContingency_R[blockIndexR] = 10;
          rwdContingencyTallyR = 0;
          rwdContingencyTallyL = 0;
          Serial.println("**************forced R probability contingency***************");
      } else {
          tempProbInd = random(sizeOfArray);
          waterContingency_R[blockIndexR] = blockArray[tempProbInd];
      }
      while (waterContingency_R[blockIndexR] == waterContingency_R[blockIndexR-1]){
          tempProbInd = random(sizeOfArray);
          waterContingency_R[blockIndexR] = blockArray[tempProbInd];
      }
      while (waterContingency_L[blockIndexL] == 10 && waterContingency_R[blockIndexR] == 10){        //pushes previous 10 port to a higher prob to keep one port from maintaining the higher prob
        blockSwitchR[blockIndexR] = blockSwitchR[blockIndexR] - blockStagger;                     //to keep blocks staggered when they both start new ones
        blockSwitchL[blockIndexL] = CSplusTrialNumber - 1;
        blockIndexL++;
      }
  }
  Serial.print("R Block Switch at Trial "); Serial.print(blockSwitchR[blockIndexR]);
  Serial.print(". Rewards (L/R) = "); Serial.print(waterContingency_L[blockIndexL]);
  Serial.print("/"); Serial.println(waterContingency_R[blockIndexR]);
}
