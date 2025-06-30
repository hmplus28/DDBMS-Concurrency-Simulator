# DDBMS Concurrency Simulator | شبیه‌ساز همروندی در پایگاه‌داده توزیع‌شده

A graphical simulator for demonstrating **Concurrency Control Mechanisms** in **Distributed Database Management Systems (DDBMS)** using Python and Tkinter.  
This project supports two major concurrency techniques: **Locking** and **Timestamp Ordering**, with visual feedback, transaction logs, and deadlock detection.

شبیه‌سازی گرافیکی برای نمایش **مکانیزم‌های کنترل همروندی** در **سامانه‌های پایگاه‌داده توزیع‌شده** با استفاده از پایتون و Tkinter.  
این پروژه از دو روش اصلی همروندی پشتیبانی می‌کند: **قفل‌گذاری (Locking)** و **مهر زمانی (Timestamping)**، با رابط کاربری تصویری، لاگ تراکنش‌ها، و تشخیص بن‌بست.

---

## 🎯 Features | امکانات

- 🔒 **Locking Protocol Simulation** (S/X locks, lock queues, upgrades)
- ⏱ **Timestamp Ordering Protocol Simulation**
- 🔄 Step-by-step execution of transactions
- 🧠 Deadlock detection and resolution
- 📊 Real-time GUI for data item states and transaction status
- 📝 Logging of all events with color-coded messages

---

## 🚀 Getting Started | شروع سریع

### Prerequisites | پیش‌نیازها

- Python 3.x  
- Tkinter (معمولاً به‌صورت پیش‌فرض همراه پایتون نصب است)

### Run the simulator | اجرای شبیه‌ساز

```bash
python main.py
