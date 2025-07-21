import time
import threading
from datetime import datetime
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw, ImageFont
from pydexcom import Dexcom
import keyring
import getpass
from win10toast import ToastNotifier
import tkinter as tk
from tkinter import simpledialog, messagebox

APP_NAME = "DexcomTrayApp"
SERVICE = "DexcomTrayService"
UPDATE_INTERVAL = 300  # seconds
LOW_THRESHOLD = 72
HIGH_THRESHOLD = 100

toaster = ToastNotifier()

def get_or_set_creds():
    user = keyring.get_password(SERVICE, "username")
    pwd = keyring.get_password(SERVICE, "password")
    region = keyring.get_password(SERVICE, "region")
    if not user or not pwd:
        # Use Tkinter dialog for credentials
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Dexcom Credentials", "Please enter your Dexcom credentials.")
        user = simpledialog.askstring("Dexcom Username", "Enter your Dexcom username:", parent=root)
        pwd = simpledialog.askstring("Dexcom Password", "Enter your Dexcom password:", show='*', parent=root)
        region = simpledialog.askstring("Dexcom Region", "Enter your Dexcom region (us/ous):", parent=root)
        if not user or not pwd:
            messagebox.showerror("Dexcom Credentials", "Username and password are required. Exiting.")
            root.destroy()
            raise RuntimeError("Dexcom credentials not provided.")
        region = (region or "us").strip().lower()
        keyring.set_password(SERVICE, "username", user)
        keyring.set_password(SERVICE, "password", pwd)
        keyring.set_password(SERVICE, "region", region)
        root.destroy()
    return user, pwd, region

def create_icon_image(value="...", trend="→", time_str="--:--"):
    image = Image.new("RGB", (64, 64), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except:
        font = ImageFont.load_default()
    draw.text((4, 4), str(value), fill="black", font=font)
    draw.text((4, 24), trend, fill="black", font=font)
    draw.text((4, 44), time_str, fill="black", font=font)
    return image

def update_loop(icon, dexcom):
    last_alert = None
    while True:
        try:
            glucose = dexcom.get_current_glucose_reading()
            value = glucose.value
            trend = glucose.trend_arrow
            timestamp = glucose.display_time.strftime("%H:%M")

            icon.icon = create_icon_image(str(value), trend, timestamp)
            icon.title = f"{value} mg/dL {trend} at {timestamp}"

            # Alerts
            if value < LOW_THRESHOLD and last_alert != "low":
                toaster.show_toast("Dexcom Alert", f"LOW: {value} mg/dL", duration=10)
                last_alert = "low"
            elif value > HIGH_THRESHOLD and last_alert != "high":
                toaster.show_toast("Dexcom Alert", f"HIGH: {value} mg/dL", duration=10)
                last_alert = "high"
            elif LOW_THRESHOLD <= value <= HIGH_THRESHOLD:
                last_alert = None

        except Exception as e:
            icon.title = f"Error: {e}"
        time.sleep(UPDATE_INTERVAL)

def main():
    username, password, region = get_or_set_creds()
    dexcom = Dexcom(account_id=username, password=password, region=region)

    icon = Icon(APP_NAME)
    icon.icon = create_icon_image("...", "→", "--:--")
    icon.menu = Menu(MenuItem("Quit", lambda icon: icon.stop()))

    threading.Thread(target=update_loop, args=(icon, dexcom), daemon=True).start()
    icon.run()

if __name__ == "__main__":
    main()
