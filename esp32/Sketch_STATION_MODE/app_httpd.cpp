// Copyright 2015-2016 Espressif Systems (Shanghai) PTE LTD
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
#include "esp_http_server.h"
#include "esp_timer.h"
#include "esp_camera.h"
#include "img_converters.h"
#include "fb_gfx.h"
#include "driver/ledc.h"

#include "sdkconfig.h"

#include "Arduino.h"
#include "sd_read_write.h"

#if defined(ARDUINO_ARCH_ESP32) && defined(CONFIG_ARDUHAL_ESP_LOG)
#include "esp32-hal-log.h"
#define TAG ""
#else
#include "esp_log.h"
static const char *TAG = "camera_httpd";
#endif

// External functions to update LCD and control backlight
extern void updateLCD(const char* line1, const char* line2);
extern void setLCDBacklight(bool on);
extern bool getLCDBacklightState();

typedef struct
{
    httpd_req_t *req;
    size_t len;
} jpg_chunking_t;

#define PART_BOUNDARY "123456789000000000000987654321"
static const char *_STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char *_STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char *_STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\nX-Timestamp: %d.%06d\r\n\r\n";

httpd_handle_t stream_httpd = NULL;
httpd_handle_t camera_httpd = NULL;

static int button_state = 1;

typedef struct
{
    size_t size;  // number of values used for filtering
    size_t index; // current value index
    size_t count; // value count
    int sum;
    int *values; // array to be filled with values
} ra_filter_t;

static ra_filter_t ra_filter;

static ra_filter_t *ra_filter_init(ra_filter_t *filter, size_t sample_size)
{
    memset(filter, 0, sizeof(ra_filter_t));

    filter->values = (int *)malloc(sample_size * sizeof(int));
    if (!filter->values)
    {
        return NULL;
    }
    memset(filter->values, 0, sample_size * sizeof(int));

    filter->size = sample_size;
    return filter;
}

static int ra_filter_run(ra_filter_t *filter, int value)
{
    if (!filter->values)
    {
        return value;
    }
    filter->sum -= filter->values[filter->index];
    filter->values[filter->index] = value;
    filter->sum += filter->values[filter->index];
    filter->index++;
    filter->index = filter->index % filter->size;
    if (filter->count < filter->size)
    {
        filter->count++;
    }
    return filter->sum / filter->count;
}

static esp_err_t stream_handler(httpd_req_t *req)
{
    camera_fb_t *fb = NULL;
    struct timeval _timestamp;
    esp_err_t res = ESP_OK;
    size_t _jpg_buf_len = 0;
    uint8_t *_jpg_buf = NULL;
    char *part_buf[128];

    static int64_t last_frame = 0;
    if (!last_frame)
    {
        last_frame = esp_timer_get_time();
    }

    res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
    if (res != ESP_OK)
    {
        return res;
    }

    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_set_hdr(req, "X-Framerate", "60");

    while (true)
    {
        fb = esp_camera_fb_get();
        if (!fb)
        {
            ESP_LOGE(TAG, "Camera capture failed");
            res = ESP_FAIL;
        }
        else
        {
            _timestamp.tv_sec = fb->timestamp.tv_sec;
            _timestamp.tv_usec = fb->timestamp.tv_usec;
            if (fb->format != PIXFORMAT_JPEG)
            {
                bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
                esp_camera_fb_return(fb);
                fb = NULL;
                if (!jpeg_converted)
                {
                    ESP_LOGE(TAG, "JPEG compression failed");
                    res = ESP_FAIL;
                }
            }
            else
            {
                _jpg_buf_len = fb->len;
                _jpg_buf = fb->buf;
            }
        }
        if (res == ESP_OK)
        {
            res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
        }
        if (res == ESP_OK)
        {
            size_t hlen = snprintf((char *)part_buf, 128, _STREAM_PART, _jpg_buf_len, _timestamp.tv_sec, _timestamp.tv_usec);
            res = httpd_resp_send_chunk(req, (const char *)part_buf, hlen);
        }
        if (res == ESP_OK)
        {
            res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
        }
        if (fb)
        {
            esp_camera_fb_return(fb);
            fb = NULL;
            _jpg_buf = NULL;
        }
        else if (_jpg_buf)
        {
            free(_jpg_buf);
            _jpg_buf = NULL;
        }
        if (res != ESP_OK)
        {
            ESP_LOGI(TAG, "res != ESP_OK : %d , break!", res);
            break;
        }
        
        // Frame delay removed for maximum speed
        
        int64_t fr_end = esp_timer_get_time();

        int64_t frame_time = fr_end - last_frame;
        last_frame = fr_end;
        frame_time /= 1000;
        uint32_t avg_frame_time = ra_filter_run(&ra_filter, frame_time);
    }
    ESP_LOGI(TAG, "Stream exit!");
    last_frame = 0;
    return res;
}

static esp_err_t parse_get(httpd_req_t *req, char **obuf)
{
    char *buf = NULL;
    size_t buf_len = 0;

    buf_len = httpd_req_get_url_query_len(req) + 1;
    if (buf_len > 1)
    {
        buf = (char *)malloc(buf_len);
        if (!buf)
        {
            httpd_resp_send_500(req);
            return ESP_FAIL;
        }
        if (httpd_req_get_url_query_str(req, buf, buf_len) == ESP_OK)
        {
            *obuf = buf;
            return ESP_OK;
        }
        free(buf);
    }
    httpd_resp_send_404(req);
    return ESP_FAIL;
}

const char index_web[]=R"rawliteral(
<html>
  <head>
    <title>ESP32-CAM Video Streaming</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 20px; }
      h1 { color: #333; }
      #stream { max-width: 100%; border: 2px solid #333; }
      button { padding: 10px 20px; margin: 5px; font-size: 16px; cursor: pointer; }
      input[type="text"] { padding: 8px; width: 200px; font-size: 14px; }
      .control-panel { margin-top: 20px; }
      .backlight-btn { padding: 15px 30px; font-size: 18px; margin: 10px; }
      .backlight-on { background-color: #4CAF50; color: white; }
      .backlight-off { background-color: #f44336; color: white; }
    </style>
  </head>
  <body>
    <h1>ESP32-CAM Video Streaming & Control</h1>
    <p><img id="stream" src="" style="transform:rotate(180deg)"/></p>
    
    <div class="control-panel">
      <h2>Controls</h2>
      <iframe width=0 height=0 frameborder=0 id="myiframe" name="myiframe"></iframe>
      <form action="/button" method="POST" target="myiframe">
        <button type="submit">Save Snapshot to SD Card</button>
      </form>
      
      <h2>LCD Backlight</h2>
      <button class="backlight-btn backlight-on" onclick="setBacklight('on')">Backlight ON</button>
      <button class="backlight-btn backlight-off" onclick="setBacklight('off')">Backlight OFF</button>
      <p id="backlight-status"></p>
      
      <h2>LCD Display</h2>
      <form action="/lcd" method="POST" target="myiframe" onsubmit="return sendLCD()">
        <label>Line 1: <input type="text" id="line1" maxlength="16" placeholder="Line 1 (16 chars)"></label><br><br>
        <label>Line 2: <input type="text" id="line2" maxlength="16" placeholder="Line 2 (16 chars)"></label><br><br>
        <button type="submit">Update LCD</button>
      </form>
      <p id="status"></p>
    </div>
  </body>
  <script>
  document.addEventListener('DOMContentLoaded', function (event) {
    var baseHost = document.location.origin;
    var streamUrl = baseHost + ':81';
    const view = document.getElementById('stream');
    view.src = `${streamUrl}/stream`;
  });
  
  function setBacklight(state) {
    fetch('/lcd/backlight', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: 'state=' + state
    })
    .then(response => response.text())
    .then(data => {
      document.getElementById('backlight-status').textContent = 'Backlight: ' + state.toUpperCase();
    })
    .catch(error => {
      document.getElementById('backlight-status').textContent = 'Error setting backlight';
    });
  }
  
  function sendLCD() {
    var line1 = document.getElementById('line1').value;
    var line2 = document.getElementById('line2').value;
    
    fetch('/lcd', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: 'line1=' + encodeURIComponent(line1) + '&line2=' + encodeURIComponent(line2)
    })
    .then(response => response.text())
    .then(data => {
      document.getElementById('status').textContent = 'LCD Updated!';
      setTimeout(() => { document.getElementById('status').textContent = ''; }, 2000);
    })
    .catch(error => {
      document.getElementById('status').textContent = 'Error updating LCD';
    });
    
    return false;
  }
  </script>
</html>)rawliteral";


static esp_err_t index_handler(httpd_req_t *req)
{
  esp_err_t err;
  err = httpd_resp_set_type(req, "text/html");
  sensor_t *s = esp_camera_sensor_get();
  if (s != NULL)
  {
      err = httpd_resp_send(req, (const char *)index_web, sizeof(index_web));
  }
  else
  {
      ESP_LOGE(TAG, "Camera sensor not found");
      err = httpd_resp_send_500(req);
  }
  return err;
}

static esp_err_t button_handler(httpd_req_t *req)
{
  esp_err_t err;
  camera_fb_t * fb = NULL;
  fb = esp_camera_fb_get();
  if (!fb)
  {
      ESP_LOGE(TAG, "Camera capture failed");
      err = ESP_FAIL;
  }
  else
  {
    String video = "/video";
    int jpgCount=readFileNum(SD_MMC, video.c_str());
    String path = video + "/" + String(jpgCount) +".jpg";
    writejpg(SD_MMC, path.c_str(), fb->buf, fb->len);
    esp_camera_fb_return(fb);
    fb = NULL;
    err=ESP_OK;
  }
  return err;
}

// Helper function to URL decode a string in place
void urlDecode(char* str) {
  char* src = str;
  char* dst = str;
  
  while (*src) {
    if (*src == '+') {
      *dst = ' ';
    } else if (*src == '%' && src[1] && src[2]) {
      // Convert hex to char
      char hex[3] = {src[1], src[2], '\0'};
      *dst = (char)strtol(hex, NULL, 16);
      src += 2;  // Skip the two hex chars
    } else {
      *dst = *src;
    }
    src++;
    dst++;
  }
  *dst = '\0';  // Null terminate the decoded string
}

// New handler for LCD display updates from Raspberry Pi
static esp_err_t lcd_handler(httpd_req_t *req)
{
  esp_err_t err = ESP_OK;
  
  // Initialize buffer to zeros to prevent garbage
  char content[200];
  memset(content, 0, sizeof(content));
  
  // Receive POST data
  int recv_size = req->content_len;
  if (recv_size > 199) recv_size = 199;
  
  int ret = httpd_req_recv(req, content, recv_size);
  
  if (ret <= 0) {
    if (ret == HTTPD_SOCK_ERR_TIMEOUT) {
      httpd_resp_send_408(req);
    }
    return ESP_FAIL;
  }
  
  content[ret] = '\0'; // Null terminate at actual received length
  
  // Debug: print raw content length and first 50 chars
  ESP_LOGI(TAG, "Received %d bytes", ret);
  
  // Initialize line buffers to all spaces (not zeros)
  char line1[17];
  char line2[17];
  for (int i = 0; i < 16; i++) {
    line1[i] = ' ';
    line2[i] = ' ';
  }
  line1[16] = '\0';
  line2[16] = '\0';
  
  // Parse line1 - copy only valid printable ASCII
  char* line1_start = strstr(content, "line1=");
  if (line1_start) {
    line1_start += 6; // Skip "line1="
    int i = 0;
    int j = 0;
    while (line1_start[i] && line1_start[i] != '&' && j < 16) {
      char c = line1_start[i];
      // Handle URL decoding inline
      if (c == '+') {
        line1[j++] = ' ';
        i++;
      } else if (c == '%' && line1_start[i+1] && line1_start[i+2]) {
        char hex[3] = {line1_start[i+1], line1_start[i+2], '\0'};
        char decoded = (char)strtol(hex, NULL, 16);
        // Only accept printable ASCII
        if (decoded >= 32 && decoded <= 126) {
          line1[j++] = decoded;
        }
        i += 3;
      } else if (c >= 32 && c <= 126) {
        // Only accept printable ASCII
        line1[j++] = c;
        i++;
      } else {
        i++;
      }
    }
  }
  
  // Parse line2 - copy only valid printable ASCII
  char* line2_start = strstr(content, "line2=");
  if (line2_start) {
    line2_start += 6; // Skip "line2="
    int i = 0;
    int j = 0;
    while (line2_start[i] && line2_start[i] != '&' && j < 16) {
      char c = line2_start[i];
      // Handle URL decoding inline
      if (c == '+') {
        line2[j++] = ' ';
        i++;
      } else if (c == '%' && line2_start[i+1] && line2_start[i+2]) {
        char hex[3] = {line2_start[i+1], line2_start[i+2], '\0'};
        char decoded = (char)strtol(hex, NULL, 16);
        // Only accept printable ASCII
        if (decoded >= 32 && decoded <= 126) {
          line2[j++] = decoded;
        }
        i += 3;
      } else if (c >= 32 && c <= 126) {
        // Only accept printable ASCII
        line2[j++] = c;
        i++;
      } else {
        i++;
      }
    }
  }
  
  ESP_LOGI(TAG, "LCD: [%s] [%s]", line1, line2);
  
  // Update the LCD
  updateLCD(line1, line2);
  
  // Send response
  httpd_resp_set_type(req, "text/plain");
  httpd_resp_send(req, "LCD Updated", HTTPD_RESP_USE_STRLEN);
  
  return err;
}

// Handler for LCD backlight control
static esp_err_t lcd_backlight_handler(httpd_req_t *req)
{
  esp_err_t err = ESP_OK;
  
  char content[50];
  memset(content, 0, sizeof(content));
  
  int recv_size = req->content_len;
  if (recv_size > 49) recv_size = 49;
  
  int ret = httpd_req_recv(req, content, recv_size);
  
  if (ret <= 0) {
    if (ret == HTTPD_SOCK_ERR_TIMEOUT) {
      httpd_resp_send_408(req);
    }
    return ESP_FAIL;
  }
  
  content[ret] = '\0';
  
  ESP_LOGI(TAG, "Backlight request: %s", content);
  
  // Parse state parameter
  if (strstr(content, "state=on") != NULL) {
    setLCDBacklight(true);
    httpd_resp_set_type(req, "text/plain");
    httpd_resp_send(req, "Backlight ON", HTTPD_RESP_USE_STRLEN);
  } else if (strstr(content, "state=off") != NULL) {
    setLCDBacklight(false);
    httpd_resp_set_type(req, "text/plain");
    httpd_resp_send(req, "Backlight OFF", HTTPD_RESP_USE_STRLEN);
  } else {
    // Return current state
    httpd_resp_set_type(req, "text/plain");
    if (getLCDBacklightState()) {
      httpd_resp_send(req, "Backlight is ON", HTTPD_RESP_USE_STRLEN);
    } else {
      httpd_resp_send(req, "Backlight is OFF", HTTPD_RESP_USE_STRLEN);
    }
  }
  
  return err;
}

void startCameraServer()
{
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.max_uri_handlers = 16;

    httpd_uri_t index_uri = {
        .uri = "/",
        .method = HTTP_GET,
        .handler = index_handler,
        .user_ctx = NULL};

    httpd_uri_t stream_uri = {
        .uri = "/stream",
        .method = HTTP_GET,
        .handler = stream_handler,
        .user_ctx = NULL}; 
    
    httpd_uri_t button_uri = {
        .uri = "/button",
        .method = HTTP_POST,
        .handler = button_handler,
        .user_ctx = NULL}; 

    httpd_uri_t lcd_uri = {
        .uri = "/lcd",
        .method = HTTP_POST,
        .handler = lcd_handler,
        .user_ctx = NULL};

    httpd_uri_t lcd_backlight_uri = {
        .uri = "/lcd/backlight",
        .method = HTTP_POST,
        .handler = lcd_backlight_handler,
        .user_ctx = NULL};

    ra_filter_init(&ra_filter, 20);

    ESP_LOGI(TAG, "Starting web server on port: '%d'", config.server_port);
    if (httpd_start(&camera_httpd, &config) == ESP_OK)
    {
        httpd_register_uri_handler(camera_httpd, &index_uri);        
        httpd_register_uri_handler(camera_httpd, &button_uri);
        httpd_register_uri_handler(camera_httpd, &lcd_uri);
        httpd_register_uri_handler(camera_httpd, &lcd_backlight_uri);
    }

    config.server_port += 1;
    config.ctrl_port += 1;
    ESP_LOGI(TAG, "Starting stream server on port: '%d'", config.server_port);
    if (httpd_start(&stream_httpd, &config) == ESP_OK)
    {
        httpd_register_uri_handler(stream_httpd, &stream_uri);
    }
}
