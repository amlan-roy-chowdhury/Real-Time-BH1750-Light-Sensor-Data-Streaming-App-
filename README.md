# Real-Time-BH1750-Light-Sensor-Data-Streaming-App-

#  Real-Time Light Sensor Dashboard

A real-time PyQt5 application that reads lux data from a light sensor (via Serial or MQTT), visualizes it live, and allows CSV export, Adafruit IO integration, and AWS S3 log storage.

---

## 📁 Project Structure

```
Real-Time Light Sensor App/
├── src/
│   ├── config.py               # Configuration and environment vars
│   ├── main.py                 # Entry point to launch the app
│   ├── core/                   # Modular business logic
│   │   ├── adafruit_uploader.py
│   │   ├── data_logger.py
│   │   ├── s3_uploader.py
│   └── ui/
│       └── layout.py           # SensorDashboard GUI class
├── test/                       # Modular test suite
│   ├── test_ui.py
│   ├── test_data.py
│   ├── test_mqtt.py
│   ├── test_export.py
│   ├── test_logger.py
│   ├── test_s3.py
│   ├── test_main.py
│   └── test_utils.py
├── logs/                       # Auto-generated log files (CSV exports, temp logs)
├── conftest.py                 # Adds src/ to sys.path for pytest
├── pytest.ini                  # Pytest config for test discovery and HTML reporting
├── report.html                 # Auto-generated test report
├── requirements.txt            # Python dependencies
└── README.md                   # You're reading it!
```

---

## 🖥️ Running the App

> Make sure you have Python 3.9+ installed, along with dependencies listed in `requirements.txt`.

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set environment variables

Create a `.env` file in the root directory:

```env
ADAFRUIT_IO_KEY=your_key_here
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_S3_BUCKET=your-bucket-name
```

### 3. Run the app

```bash
python src/main.py
```

> The app launches with a dashboard to stream lux data, export CSVs, upload to Adafruit IO, and sync to AWS S3.

---

## 🧪 Running Tests

This project uses **pytest** with modular test files.

### ✅ Run all tests:

```bash
pytest
```

### 📊 Run tests with coverage:

```bash
pytest --cov=src --cov-report=term-missing
```

### 🌐 Generate an HTML report:

```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

> You'll get a browser-based, line-by-line coverage report with color coding.

---

## 📈 Output

- Logs are saved to the `/logs/` folder
- Exports include min, max, avg values
- Failed exports are saved as `temp_log.csv` until cleared
- Data is also published live to Adafruit IO every 2 seconds

---

## 🚀 Features

- Real-time sensor data visualization from BH1750 (via ESP32)
- Dynamic UI time mode switching: Relative and GMT
- Dual stream mode: WiFi (MQTT) or COM (USB Serial)
- Cloud sync with Adafruit IO (live) and AWS S3 + RDS (batch)
- CSV Export with summary stats (Min, Max, Avg)
- Grafana dashboard for historical data
- Full cross-platform support (Windows, macOS)
- Realtime matplotlib plotting
- Data export with full stats
- Temp log recovery
- Adafruit IO push + AWS S3 upload
- Modular, testable architecture (84%+ coverage)
- Pytest HTML and coverage reports

---

## 🔮 Future Improvements

- CI/CD with GitHub Actions (pytest on push)
- Dark mode UI toggle
- Real-time cloud dashboard using Grafana + PostgreSQL
- Dockerized deployment with one-click launch

---

## 📦 Other Downloads

| Platform | Version | Download |
|----------|---------|----------|
| Windows (.exe) | v1.2.4 | [sensor_dashboard_windows.zip](https://github.com/amlan-roy-chowdhury/Real-Time-BH1750-Light-Sensor-Data-Streaming-App-/releases/download/v1.2.4/sensor_dashboard_windows.zip) |
| macOS (.app) | Coming soon | TBD |

---

## 📋 Changelog

| Version | Notes |
|---------|-------|
| v1.2.4  | Initial automated Windows release with zipped `.exe` |
| _..._   | _More releases coming soon_ |

---

## 🪟 Download for Windows

📦 **[Download sensor_dashboard_windows.zip](https://github.com/amlan-roy-chowdhury/Real-Time-BH1750-Light-Sensor-Data-Streaming-App-/releases/download/v1.2.4/sensor_dashboard_windows.zip)**  
💡 No installation required – just unzip and run the `.exe`.

### ⚙️ How to Use:
1. Download and unzip the archive
2. Double-click `sensor_dashboard.exe` to launch the app
3. If prompted with a security warning:
   - Click **More Info** → **Run anyway**

---

## 🔧 Coming Soon

- MSI Installer for Windows
- macOS release `.dmg`
- OTA update checker
- Platform-independent launcher

## 🧑‍💻 Developed By

**Amlan Chowdhury**  
https://github.com/amlan-roy-chowdhury

---

## 📝 License

MIT License
