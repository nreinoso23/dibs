#include "sd_read_write.h"

// External reference to SERIAL_PORT defined in main sketch
#define SERIAL_PORT Serial0

void sdmmcInit(void){
  SD_MMC.setPins(SD_MMC_CLK, SD_MMC_CMD, SD_MMC_D0);
  if (!SD_MMC.begin("/sdcard", true, true, SDMMC_FREQ_DEFAULT, 5)) {
    SERIAL_PORT.println("Card Mount Failed");
    return;
  }
  uint8_t cardType = SD_MMC.cardType();
  if(cardType == CARD_NONE){
      SERIAL_PORT.println("No SD_MMC card attached");
      return;
  }
  SERIAL_PORT.print("SD_MMC Card Type: ");
  if(cardType == CARD_MMC){
      SERIAL_PORT.println("MMC");
  } else if(cardType == CARD_SD){
      SERIAL_PORT.println("SDSC");
  } else if(cardType == CARD_SDHC){
      SERIAL_PORT.println("SDHC");
  } else {
      SERIAL_PORT.println("UNKNOWN");
  }
  uint64_t cardSize = SD_MMC.cardSize() / (1024 * 1024);
  SERIAL_PORT.printf("SD_MMC Card Size: %lluMB\n", cardSize);  
  SERIAL_PORT.printf("Total space: %lluMB\r\n", SD_MMC.totalBytes() / (1024 * 1024));
  SERIAL_PORT.printf("Used space: %lluMB\r\n", SD_MMC.usedBytes() / (1024 * 1024));
}

void listDir(fs::FS &fs, const char * dirname, uint8_t levels){
    SERIAL_PORT.printf("Listing directory: %s\n", dirname);

    File root = fs.open(dirname);
    if(!root){
        SERIAL_PORT.println("Failed to open directory");
        return;
    }
    if(!root.isDirectory()){
        SERIAL_PORT.println("Not a directory");
        return;
    }

    File file = root.openNextFile();
    while(file){
        if(file.isDirectory()){
            SERIAL_PORT.print("  DIR : ");
            SERIAL_PORT.println(file.name());
            if(levels){
                listDir(fs, file.path(), levels -1);
            }
        } else {
            SERIAL_PORT.print("  FILE: ");
            SERIAL_PORT.print(file.name());
            SERIAL_PORT.print("  SIZE: ");
            SERIAL_PORT.println(file.size());
        }
        file = root.openNextFile();
    }
}

void createDir(fs::FS &fs, const char * path){
    SERIAL_PORT.printf("Creating Dir: %s\n", path);
    if(fs.mkdir(path)){
        SERIAL_PORT.println("Dir created");
    } else {
        SERIAL_PORT.println("mkdir failed");
    }
}

void removeDir(fs::FS &fs, const char * path){
    SERIAL_PORT.printf("Removing Dir: %s\n", path);
    if(fs.rmdir(path)){
        SERIAL_PORT.println("Dir removed");
    } else {
        SERIAL_PORT.println("rmdir failed");
    }
}

void readFile(fs::FS &fs, const char * path){
    SERIAL_PORT.printf("Reading file: %s\n", path);

    File file = fs.open(path);
    if(!file){
        SERIAL_PORT.println("Failed to open file for reading");
        return;
    }

    SERIAL_PORT.print("Read from file: ");
    while(file.available()){
        SERIAL_PORT.write(file.read());
    }
}

void writeFile(fs::FS &fs, const char * path, const char * message){
    SERIAL_PORT.printf("Writing file: %s\n", path);

    File file = fs.open(path, FILE_WRITE);
    if(!file){
        SERIAL_PORT.println("Failed to open file for writing");
        return;
    }
    if(file.print(message)){
        SERIAL_PORT.println("File written");
    } else {
        SERIAL_PORT.println("Write failed");
    }
}

void appendFile(fs::FS &fs, const char * path, const char * message){
    SERIAL_PORT.printf("Appending to file: %s\n", path);

    File file = fs.open(path, FILE_APPEND);
    if(!file){
        SERIAL_PORT.println("Failed to open file for appending");
        return;
    }
    if(file.print(message)){
        SERIAL_PORT.println("Message appended");
    } else {
        SERIAL_PORT.println("Append failed");
    }
}

void renameFile(fs::FS &fs, const char * path1, const char * path2){
    SERIAL_PORT.printf("Renaming file %s to %s\n", path1, path2);
    if (fs.rename(path1, path2)) {
        SERIAL_PORT.println("File renamed");
    } else {
        SERIAL_PORT.println("Rename failed");
    }
}

void deleteFile(fs::FS &fs, const char * path){
    SERIAL_PORT.printf("Deleting file: %s\n", path);
    if(fs.remove(path)){
        SERIAL_PORT.println("File deleted");
    } else {
        SERIAL_PORT.println("Delete failed");
    }
}

void testFileIO(fs::FS &fs, const char * path){
    File file = fs.open(path);
    static uint8_t buf[512];
    size_t len = 0;
    uint32_t start = millis();
    uint32_t end = start;
    if(file){
        len = file.size();
        size_t flen = len;
        start = millis();
        while(len){
            size_t toRead = len;
            if(toRead > 512){
                toRead = 512;
            }
            file.read(buf, toRead);
            len -= toRead;
        }
        end = millis() - start;
        SERIAL_PORT.printf("%u bytes read for %u ms\r\n", flen, end);
        file.close();
    } else {
        SERIAL_PORT.println("Failed to open file for reading");
    }

    file = fs.open(path, FILE_WRITE);
    if(!file){
        SERIAL_PORT.println("Failed to open file for writing");
        return;
    }

    size_t i;
    start = millis();
    for(i=0; i<2048; i++){
        file.write(buf, 512);
    }
    end = millis() - start;
    SERIAL_PORT.printf("%u bytes written for %u ms\n", 2048 * 512, end);
    file.close();
}

void writejpg(fs::FS &fs, const char * path, const uint8_t *buf, size_t size){
    File file = fs.open(path, FILE_WRITE);
    if(!file){
      SERIAL_PORT.println("Failed to open file for writing");
      return;
    }
    file.write(buf, size);
    SERIAL_PORT.printf("Saved file to path: %s\r\n", path);
}

int readFileNum(fs::FS &fs, const char * dirname){
    File root = fs.open(dirname);
    if(!root){
        SERIAL_PORT.println("Failed to open directory");
        return -1;
    }
    if(!root.isDirectory()){
        SERIAL_PORT.println("Not a directory");
        return -1;
    }

    File file = root.openNextFile();
    int num=0;
    while(file){
      file = root.openNextFile();
      num++;
    }
    return num;  
}
