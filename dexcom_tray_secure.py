import time
import threading
from datetime import datetime
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw, ImageFont
from pydexcom import Dexcom
import keyring
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
    """Retrieve or prompt for Dexcom credentials using keyring and Tkinter dialogs."""
    user = keyring.get_password(SERVICE, "username")
    pwd = keyring.get_password(SERVICE, "password")
    region = keyring.get_password(SERVICE, "region")
    if not user or not pwd:
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
    if not region:
        region = "us"
    return user, pwd, region

def create_icon_image(value="...", trend="→", time_str="--:--"):
    """Create a tray icon image showing glucose value, trend, and time."""
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))  # Transparent background
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 28)  # Larger font
        small_font = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    draw.text((8, 0), str(value), fill="black", font=font)
    draw.text((8, 32), trend, fill="blue", font=small_font)
    draw.text((8, 48), time_str, fill="gray", font=small_font)
    return image

def update_loop(icon, dexcom):
    """Background loop to update tray icon and show notifications."""
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
            icon.icon = create_icon_image("Err", "!", "--:--")
            icon.title = f"Error: {e}"
        time.sleep(UPDATE_INTERVAL)

def show_last_reading(icon, dexcom):
    """Show the last glucose reading in a message box."""
    try:
        glucose = dexcom.get_current_glucose_reading()
        value = glucose.value
        trend = glucose.trend_arrow
        timestamp = glucose.display_time.strftime("%H:%M")
        messagebox.showinfo("Last Reading", f"{value} mg/dL {trend} at {timestamp}")
    except Exception as e:
        messagebox.showerror("Error", str(e))

def clear_credentials(icon):
    """Clear stored Dexcom credentials."""
    keyring.delete_password(SERVICE, "username")
    keyring.delete_password(SERVICE, "password")
    keyring.delete_password(SERVICE, "region")
    messagebox.showinfo("Credentials", "Credentials cleared. Restart app to re-enter.")

def main():
    """Main entry point for the tray app."""
    username, password, region = get_or_set_creds()
    dexcom = Dexcom(username=username, password=password, region=region)

    icon = Icon(APP_NAME)
    icon.icon = create_icon_image("...", "→", "--:--")
    icon.menu = Menu(
        MenuItem("Show Last Reading", lambda _: show_last_reading(icon, dexcom)),
        MenuItem("Clear Credentials", lambda _: clear_credentials(icon)),
        MenuItem("Quit", lambda _: icon.stop())
    )

    threading.Thread(target=update_loop, args=(icon, dexcom), daemon=True).start()
    icon.run()

if __name__ == "__main__":
    main()
