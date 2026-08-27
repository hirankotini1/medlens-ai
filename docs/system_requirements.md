# System Requirements Specification

---

## 1. Hardware Requirements

### Development & Server Environment
* **Processor:** Intel Core i3 / AMD Ryzen 3 or higher (Quad-core 2.0 GHz+ recommended)
* **RAM:** 4 GB minimum (8 GB recommended for simultaneous OpenCV feature extraction and dev server execution)
* **Storage:** 2 GB available hard drive space for repository, dependencies, SQLite database, and model artifacts
* **Network:** Standard TCP/IP network interface (Loopback for local development; 10 Mbps+ for LAN/WAN deployment)

### Client Environment
* **Device:** Desktop PC, Laptop, Tablet, or Smartphone
* **Display Resolution:** 360x640 (Mobile) up to 1920x1080 (Full HD Desktop)
* **Browser:** Google Chrome 90+, Mozilla Firefox 88+, Microsoft Edge 90+, or Apple Safari 14+

---

## 2. Software Requirements

### Backend & Machine Learning Stack
* **Operating System:** Windows 10/11, Ubuntu Linux 20.04+, or macOS 12+
* **Runtime Environment:** Python 3.10, 3.11, or 3.12
* **Web Framework:** FastAPI 0.115+
* **ASGI Server:** Uvicorn 0.34+
* **Data Science & ML Libraries:**
  * `scikit-learn` 1.6+
  * `pandas` 2.2+
  * `numpy` 2.0+
  * `joblib` 1.4+
  * `opencv-python` 4.10+
  * `scipy` 1.14+
* **Validation & Security:**
  * `pydantic` 2.10+
  * `hashlib` (Standard Library: PBKDF2-HMAC-SHA256)
  * `hmac` & `secrets` (Standard Library: Cryptographic signature & token generation)

### Database Layer
* **DBMS:** SQLite 3.35+ (Native Python `sqlite3` driver with row factory support and online backup API)

### Frontend Layer
* **Markup:** Semantic HTML5
* **Styling:** Modern CSS3 (Vanilla CSS with CSS Variables, Flexbox, Grid, Backdrop Blur & `@media print`)
* **Client Scripting:** Modern Vanilla JavaScript (ES6+ with `async/await`, Fetch API, and DOM manipulation)
* **Typography:** Google Fonts (`Plus Jakarta Sans`)
