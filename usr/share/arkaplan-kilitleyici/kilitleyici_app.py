#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import webbrowser
import tkinter.font as tkFont
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import shutil
import subprocess

# =============================================================================
# SABİT DEĞİŞKENLER (Sistem Yolları)
# =============================================================================

# Resimlerin kopyalanacağı sistem klasörü
BG_DIR = "/usr/share/backgrounds/"

# dconf ayar dosyalarının yolları
DCONF_PROFILE = "/etc/dconf/profile/user"
DCONF_LOCK_DIR = "/etc/dconf/db/local.d/locks"
DCONF_DEFAULT_FILE = "/etc/dconf/db/local.d/00-etap-background-default"
DCONF_LOCK_FILE = os.path.join(DCONF_LOCK_DIR, "00-etap-background-lock")

# Kilitlenecek Cinnamon ayar anahtarları
DCONF_LOCK_CONTENT = """/org/cinnamon/desktop/background/picture-uri
/org/cinnamon/desktop/background/picture-options
"""

# dconf profil içeriği
DCONF_PROFILE_CONTENT = """user-db:user
system-db:local
"""

# =============================================================================
# UYGULAMA MANTIĞI (Backend Fonksiyonları)
# =============================================================================

def check_root_permissions():
    """Script'in root olarak çalışıp çalışmadığını kontrol eder."""
    if os.geteuid() != 0:
        messagebox.showerror(
            "Yönetici İzni Gerekli",
            "Bu uygulama sistem dosyalarını değiştireceğinden yönetici (root) olarak çalıştırılmalıdır.\n\n"
            "Lütfen terminalden şu komutla çalıştırın:\n"
            "sudo python3 kilitleyici_app.py"
        )
        return False
    return True

def run_command(command_list):
    """Terminal komutlarını güvenle çalıştırır."""
    try:
        subprocess.run(command_list, check=True, capture_output=True, text=True)
        return True, ""
    except subprocess.CalledProcessError as e:
        print(f"Komut Hatası: {e.stderr}")
        return False, e.stderr

def create_dconf_structure():
    """Gerekli /etc/dconf klasörlerini oluşturur."""
    os.makedirs(DCONF_LOCK_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(DCONF_PROFILE), exist_ok=True)
    
def write_file(filepath, content):
    """Verilen yola, verilen içeriği yazar."""
    with open(filepath, 'w') as f:
        f.write(content)

def do_lock_background(image_path):
    """Arka planı kilitleme işleminin ana mantığı."""
    status_label.config(text="Durum: İşlem yapılıyor...")
    app.update_idletasks() # Arayüzü güncel tutar

    try:
        # 1. Resim dosyasını kopyala (veya atla)
        file_name = os.path.basename(image_path)
        dest_path = os.path.join(BG_DIR, file_name)

        if image_path == dest_path:
            status_label.config(text="Durum: [1/5] Resim zaten sistem klasöründe, kopyalama atlanıyor...")
            # Kopyalama adımını atla, çünkü dosya zaten yerinde
        else:
            status_label.config(text="Durum: [1/5] Resim kopyalanıyor...")
            shutil.copy2(image_path, dest_path)
        
        # 2. Gerekli dconf dizinlerini oluştur
        status_label.config(text="Durum: [2/5] Dizinler oluşturuluyor...")
        
        # 3. dconf profil dosyasını yaz
        status_label.config(text="Durum: [3/5] Profil dosyası yazılıyor...")
        write_file(DCONF_PROFILE, DCONF_PROFILE_CONTENT)

        # 4. dconf kilit dosyasını yaz
        status_label.config(text="Durum: [4/5] Kilit dosyası yazılıyor...")
        write_file(DCONF_LOCK_FILE, DCONF_LOCK_CONTENT)
        
        # 5. dconf varsayılan ayar dosyasını yaz
        status_label.config(text="Durum: [5/5] Varsayılan ayar yazılıyor...")
        dconf_uri = f"file://{dest_path}"
        default_content = f"""
[org/cinnamon/desktop/background]
picture-uri='{dconf_uri}'
picture-options='zoom'
"""
        write_file(DCONF_DEFAULT_FILE, default_content)

        # 6. Veritabanını güncelle
        status_label.config(text="Durum: Veritabanı güncelleniyor...")
        success, error = run_command(['dconf', 'update'])
        if not success:
            raise Exception(f"dconf update başarısız oldu: {error}")

        status_label.config(text="Durum: Başarılı!")
        messagebox.showinfo(
            "İşlem Tamamlandı",
            "Arka plan başarıyla kilitlendi.\n\n"
            "Değişikliklerin geçerli olması için lütfen tahtayı YENİDEN BAŞLATIN."
        )

    except Exception as e:
        status_label.config(text="Durum: Hata!")
        messagebox.showerror("Hata", f"İşlem sırasında bir hata oluştu:\n{str(e)}")

def do_unlock_background():
    """Arka plan kilidini kaldırma işleminin ana mantığı."""
    status_label.config(text="Durum: Kilit kaldırılıyor...")
    
    try:
        # Kilidi kaldırmak için ilgili ayar dosyalarını silmek yeterlidir.
        files_to_remove = [DCONF_DEFAULT_FILE, DCONF_LOCK_FILE]
        removed_count = 0
        
        for f in files_to_remove:
            if os.path.exists(f):
                os.remove(f)
                removed_count += 1
        
        if removed_count == 0:
            status_label.config(text="Durum: Hazır.")
            messagebox.showinfo("Bilgi", "Sistem zaten kilitli görünmüyor (ayar dosyaları bulunamadı).")
            return

        # Veritabanını güncelle
        status_label.config(text="Durum: Veritabanı güncelleniyor...")
        success, error = run_command(['dconf', 'update'])
        if not success:
            raise Exception(f"dconf update başarısız oldu: {error}")

        status_label.config(text="Durum: Başarılı!")
        messagebox.showinfo(
            "İşlem Tamamlandı",
            "Arka plan kilidi kaldırıldı.\n\n"
            "Değişikliklerin geçerli olması için lütfen tahtayı YENİDEN BAŞLATIN."
        )

    except Exception as e:
        status_label.config(text="Durum: Hata!")
        messagebox.showerror("Hata", f"İşlem sırasında bir hata oluştu:\n{str(e)}")

# =============================================================================
# ARAYÜZ KODU (GUI Fonksiyonları)
# =============================================================================

def gui_browse_file():
    """Gözat düğmesine basıldığında çalışır."""
    filepath = filedialog.askopenfilename(
        title="Arka Plan Resmini Seçin",
        filetypes=[("Resim Dosyaları", "*.png *.jpg *.jpeg *.webp"), ("Tüm Dosyalar", "*.*")]
    )
    if filepath:
        selected_file_path.set(filepath)
        status_label.config(text=f"Seçildi: {os.path.basename(filepath)}")

def gui_lock_button_pressed():
    """Kilitle düğmesine basıldığında çalışır."""
    filepath = selected_file_path.get()
    if not filepath:
        messagebox.showwarning("Eksik Bilgi", "Lütfen önce 'Gözat' düğmesi ile bir resim seçin.")
        return
        
    if not os.path.exists(filepath):
        messagebox.showerror("Hata", f"Seçilen dosya bulunamadı:\n{filepath}")
        return
        
    do_lock_background(filepath)

def gui_unlock_button_pressed():
    """Kilidi Kaldır düğmesine basıldığında çalışır."""
    if messagebox.askyesno(
        "Onay", 
        "Arka plan kilidini kaldırmak istediğinizden emin misiniz?\n"
        "Kullanıcılar yeniden arka planı değiştirebilecek."
    ):
        do_unlock_background()
        
def open_school_website(event):
    """Okul web sitesini açar."""
    try:
        webbrowser.open_new_tab("https://tsomtal.meb.k12.tr")
    except Exception as e:
        print(f"Hata: Web sitesi açılamadı: {e}")

# =============================================================================
# ANA UYGULAMA VE ARAYÜZ KURULUMU
# =============================================================================

if __name__ == "__main__":
    app = tk.Tk()
    app.title("Pardus ETAP Arka Plan Kilitleyici")
    app.geometry("500x200")

    # Yönetici haklarını kontrol et
    #if not check_root_permissions():
    #    app.destroy()  # root değilse uygulamayı hemen kapat
    #    exit()

    selected_file_path = tk.StringVar()

    # --- Üst Çerçeve (Gözat) ---
    top_frame = tk.Frame(app, pady=10, padx=10)
    top_frame.pack(fill="x")

    browse_button = tk.Button(top_frame, text="1. Arka Plan Resmi Seç (Gözat)", command=gui_browse_file)
    browse_button.pack(side="left", padx=(0, 10))

    file_label = tk.Label(top_frame, textvariable=selected_file_path, relief="sunken", anchor="w", bg="#ffffff")
    file_label.pack(side="left", fill="x", expand=True)

    # --- Orta Çerçeve (Eylem Düğmeleri) ---
    mid_frame = tk.Frame(app, pady=10, padx=10)
    mid_frame.pack(fill="both", expand=True)

    lock_button = tk.Button(
        mid_frame, 
        text="2. KİLİTLE ve AYARLA", 
        command=gui_lock_button_pressed, 
        bg="#d4edda", 
        fg="#155724",
        height=3
    )
    lock_button.pack(side="left", fill="both", expand=True, padx=(0, 5))

    unlock_button = tk.Button(
        mid_frame, 
        text="Kilidi Kaldır", 
        command=gui_unlock_button_pressed, 
        bg="#f8d7da", 
        fg="#721c24",
        height=3
    )
    unlock_button.pack(side="right", fill="both", expand=True, padx=(5, 0))

    # --- Alt Çerçeve (Durum Çubuğu ve Link) ---
    bottom_frame = tk.Frame(app, relief="sunken", bd=1)
    bottom_frame.pack(side="bottom", fill="x")

    status_label = tk.Label(bottom_frame, text="Durum: Hazır.", anchor="w", padx=5)
    status_label.pack(side="left", fill="x", expand=True) # Durum yazısı sola yaslansın ve yayılsın

    # Okul linki
    link_label = tk.Label(bottom_frame, text="TSOMTAL", fg="blue", cursor="hand2", padx=5)
    
    # Mevcut fontu alıp altını çizili yap
    link_font = tkFont.Font(link_label, link_label.cget("font"))
    link_font.configure(underline=True)
    link_label.configure(font=link_font)
    
    link_label.pack(side="right") # Link sağa yaslansın
    link_label.bind("<Button-1>", open_school_website) # Tıklama olayını bağla


    # Uygulamayı başlat
    app.mainloop()
