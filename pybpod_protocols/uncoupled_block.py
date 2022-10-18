'''
Generate uncoupled block reward schedule

adapted from Cohen lab's Arduino code
'''

import numpy as np



block_min = 20;
block_max = 35;
block_reward_prob = [0.1, 0.5, 0.9];

perseve_add = True
byte perseverativeLimit = 4;

bool autoPauseFlag = true;
const byte maxNonLickTrials = 2; // max number of trials without a lick
unsigned long pauseDuration = 30000; // pause for this many ms

bool noLickWindowFlag = true;
bool ITIlickDelay = false;
const int timeoutTime = 1500;
const int rwdDelay = 200;
const int noLickWindow_duration = 1000;
const int maxITI = 15;

// -------------------------------------------------------------------------------------------------------------
// variables that shouldn't be changed--------------------------------------------------------------------------

byte consecWaterRNotDelivered = 0;
byte consecWaterLNotDelivered = 0;
byte consecNonLickTrials = 0;
byte numPersevAdd = 0;
byte numAutoPauses = 0;
bool noLickFlag = false;
bool solRetractedDueToPersev = false;

byte blockIndexL = 0;
byte blockIndexR = 0;
byte blockStagger = (round(blockMax - blockMin - 0.5) / 2 + blockMin) / 2;


  Serial.println();
  task.generateFirstBlock(blockMin, blockMax, blockArray, blockIndexL, blockIndexR, blockStagger);
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
      task.generateNextBlockL(blockMin, blockMax, blockArray, blockIndexL, blockIndexR, blockStagger);
    }
    if ((task.CSplusTrialNumber > task.blockSwitchR[blockIndexR])){
      blockIndexR++; 
      Serial.println();
      task.generateNextBlockR(blockMin, blockMax, blockArray, blockIndexL, blockIndexR, blockStagger);
      if ((task.CSplusTrialNumber > task.blockSwitchL[blockIndexL])){
        blockIndexL++; 
        Serial.println();
        task.generateNextBlockL(blockMin, blockMax, blockArray, blockIndexL, blockIndexR, blockStagger);
      }
    }
    Serial.println();
    Serial.print("L Trial "); Serial.print(task.CSplusTrialNumber); Serial.print("(");
    Serial.print(trialNumber); Serial.print(") of "); Serial.println(task.blockSwitchL[blockIndexL]);
    Serial.print("R                      of ");Serial.println(task.blockSwitchR[blockIndexR]);
    Serial.print("Contingency (L/R). "); Serial.print(task.waterContingency_L[blockIndexL]);
    Serial.print("/"); Serial.print(task.waterContingency_R[blockIndexR]);
    Serial.print(": "); Serial.println(millis());

    if (noLickWindowFlag) {
      noLickFlag = false;
      noLickWindow();
    }
    
    CSplusFlag = false;
    task.clearTouchAndRewardFlags(); // clears anyLick and rewardDelivered for L and R

    if (random(100) <= task.CSplus_prob){ // CSplus trial
      CSplusFlag = true;
      CSplusRoutine(); 
    } else {
      CSminusRoutine();
    }

    preITIRoutine();
    if (!solRetractedDueToPersev){ // release the solenoid if it was pulled back due to 
      task.releaseSolenoid();
    }
    ITI_Exp();
    Serial.print("\t\tTotal Reward Volume: "); Serial.println((task.totalRewardL + task.totalRewardR)*waterVolume);

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


void taskSettings::generateFirstBlock(int blockMin, int blockMax, int blockArray[], int blockIndexL, int blockIndexR, int blockStagger, int sizeOfArray){
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
        taskSettings::generateNextBlockL(blockMin, blockMax, blockArray, blockIndexL, blockIndexR, blockStagger, sizeOfArray);
        delay(5);
        taskSettings::generateNextBlockR(blockMin, blockMax, blockArray, blockIndexL, blockIndexR, blockStagger, sizeOfArray);
    }else{
        taskSettings::generateNextBlockR(blockMin, blockMax, blockArray, blockIndexL, blockIndexR, blockStagger, sizeOfArray);
        delay(5);
        taskSettings::generateNextBlockL(blockMin, blockMax, blockArray, blockIndexL, blockIndexR, blockStagger, sizeOfArray);
    }
    if (waterContingency_L[0] <= waterContingency_R[0]){
        blockSwitchL[blockIndexL] = blockSwitchL[blockIndexL] - blockStagger;  
    }else{
        blockSwitchR[blockIndexR] = blockSwitchR[blockIndexR] - blockStagger; 
  }
}


void taskSettings::generateNextBlockL(int blockMin, int blockMax, int blockArray[], int blockIndexL, int blockIndexR, int blockStagger, int sizeOfArray){
    // generate new block 1 at a time; allows for flexibility in changing blockMin/blockMax
    if (blockIndexL == 0){
        blockSwitchL[blockIndexL] = random(blockMax - blockMin + 1) + blockMin; // init first as rand
        if (randomBlockProbs == true){
            tempProbInd = random(sizeOfArray);
            waterContingency_L[0] = blockArray[tempProbInd];
            while (waterContingency_L[blockIndexL] == 10 && waterContingency_R[blockIndexR] == 10){
                tempProbInd = random(sizeOfArray);
                waterContingency_R[blockIndexR] = blockArray[tempProbInd];
            }
        }
    } else {
        blockSwitchL[blockIndexL] = random(blockMax - blockMin + 1) + blockMin + blockSwitchL[blockIndexL-1];
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

void taskSettings::generateNextBlockR(int blockMin, int blockMax, int blockArray[], int blockIndexL, int blockIndexR, int blockStagger, int sizeOfArray){
    // generate new block 1 at a time; allows for flexibility in changing blockMin/blockMax
    if (blockIndexR == 0){
        blockSwitchR[blockIndexR] = random(blockMax - blockMin + 1) + blockMin; // init first as rand
        if (randomBlockProbs == true){
            tempProbInd = random(sizeOfArray);
            waterContingency_R[0] = blockArray[tempProbInd];
            while (waterContingency_L[blockIndexL] == 10 && waterContingency_R[blockIndexR] == 10){
                tempProbInd = random(sizeOfArray);
                waterContingency_R[blockIndexR] = blockArray[tempProbInd];
            }
        }    
    } else {
        blockSwitchR[blockIndexR] = random(blockMax - blockMin + 1) + blockMin + blockSwitchR[blockIndexR-1];
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
