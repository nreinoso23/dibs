/**********************************************************************
  Filename    : Video Web Server STATION MODE - QVGA Version
  Description : Connects to existing WiFi router instead of creating AP
               Much more stable and faster than AP mode!
  Resolution  : QVGA (320x240) for speed
  Modified    : 2025/11/14
**********************************************************************/
#include "esp_camera.h"
#include <WiFi.h>
#include "sd_read_write.h"
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// Select camera model
#define CAMERA_MODEL_ESP32S3_EYE

#define SERIAL_PORT Serial0

#include "camera_pins.h"

// WiFi credentials - CHANGE THESE to your router!
const char* ssid = "nyu-android";         // ← Change this!
const char* password = "dr0idz-2o2!"; // ← Change this!

// I2C LCD Configuration
#define LCD_ADDRESS 0x27
#define LCD_COLUMNS 16
#define LCD_ROWS 2
#define I2C_SDA 41
#define I2C_SCL 42

LiquidCrystal_I2C lcd(LCD_ADDRESS, LCD_COLUMNS, LCD_ROWS);

// Track backlight state
bool lcdBacklightOn = true;

void cameraInit(void);
void startCameraServer();
void lcdInit(void);

void setup() {
  SERIAL_PORT.begin(115200);
  delay(1000);
  SERIAL_PORT.println("\n\nBooting camera server (STATION MODE)...");

  // Initialize I2C LCD
  lcdInit();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Initializing...");

  // Initialize camera
  cameraInit();
  
  // Initialize SD card (optional - comment out if causing issues)
  sdmmcInit();
  removeDir(SD_MMC, "/video");
  createDir(SD_MMC, "/video");
  
  // Connect to WiFi Router (STATION MODE)
  SERIAL_PORT.println("Connecting to WiFi...");
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Connecting WiFi");
  
  WiFi.mode(WIFI_STA);  // Station mode (not AP!)
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    SERIAL_PORT.print(".");
    lcd.setCursor(attempts % 16, 1);
    lcd.print(".");
    attempts++;
  }
  
  if (WiFi.status() != WL_CONNECTED) {
    SERIAL_PORT.println("\nFailed to connect to WiFi!");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Failed!");
    lcd.setCursor(0, 1);
    lcd.print("Check settings");
    return;
  }
  
  SERIAL_PORT.println("\nWiFi connected!");
  IPAddress IP = WiFi.localIP();
  SERIAL_PORT.print("IP address: ");
  SERIAL_PORT.println(IP);
  
  // Display on LCD
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Connected!");
  lcd.setCursor(0, 1);
  lcd.print(IP);

  // Start camera server
  startCameraServer();

  SERIAL_PORT.println("\n========================================");
  SERIAL_PORT.println("Camera Ready! STATION MODE (QVGA)");
  SERIAL_PORT.println("========================================");
  SERIAL_PORT.print("Stream URL: http://");
  SERIAL_PORT.print(IP);
  SERIAL_PORT.println(":81/stream");
  SERIAL_PORT.print("Web interface: http://");
  SERIAL_PORT.println(IP);
  SERIAL_PORT.println("========================================\n");
}

void loop() {
  // Monitor connection
  if (WiFi.status() != WL_CONNECTED) {
    SERIAL_PORT.println("WiFi connection lost! Reconnecting...");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Reconnecting...");
    WiFi.reconnect();
  }
  delay(10000);
}

void lcdInit(void) {
  SERIAL_PORT.println("Starting LCD initialization...");
  Wire.begin(I2C_SDA, I2C_SCL);
  delay(100);
  
  lcd.init();
  lcd.backlight();
  lcdBacklightOn = true;
  delay(100);
  
  SERIAL_PORT.println("LCD initialized!");
}

void cameraInit(void){
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 10000000;
  
  // QVGA for maximum speed and stability
  config.frame_size = FRAMESIZE_QVGA;    // 320x240
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_LATEST;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 20;
  config.fb_count = 2;
  
  if(psramFound()){
    SERIAL_PORT.println("PSRAM found - optimized settings active");
  } else {
    SERIAL_PORT.println("WARNING: No PSRAM!");
    config.fb_location = CAMERA_FB_IN_DRAM;
    config.fb_count = 1;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    SERIAL_PORT.printf("Camera init failed: 0x%x\n", err);
    lcd.clear();
    lcd.print("Camera FAILED!");
    return;
  }

  sensor_t * s = esp_camera_sensor_get();
  s->set_vflip(s, 1);
  s->set_brightness(s, 1);
  s->set_saturation(s, 0);
  
  SERIAL_PORT.println("Camera initialized - QVGA mode!");
}

void updateLCD(const char* line1, const char* line2) {
  // Write line1 character by character, pad with spaces
  lcd.setCursor(0, 0);
  for (int i = 0; i < 16; i++) {
    if (line1[i] != '\0') {
      lcd.write(line1[i]);
    } else {
      // Once we hit null, pad rest with spaces
      for (int j = i; j < 16; j++) {
        lcd.write(' ');
      }
      break;
    }
  }
  
  // Write line2 character by character, pad with spaces
  lcd.setCursor(0, 1);
  for (int i = 0; i < 16; i++) {
    if (line2[i] != '\0') {
      lcd.write(line2[i]);
    } else {
      // Once we hit null, pad rest with spaces
      for (int j = i; j < 16; j++) {
        lcd.write(' ');
      }
      break;
    }
  }
}

// Control LCD backlight on/off
void setLCDBacklight(bool on) {
  if (on && !lcdBacklightOn) {
    lcd.backlight();
    lcdBacklightOn = true;
    SERIAL_PORT.println("LCD backlight ON");
  } else if (!on && lcdBacklightOn) {
    lcd.noBacklight();
    lcdBacklightOn = false;
    SERIAL_PORT.println("LCD backlight OFF");
  }
}

// Get current backlight state
bool getLCDBacklightState() {
  return lcdBacklightOn;
}
