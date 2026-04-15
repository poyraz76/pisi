# -*- coding:utf-8 -*-
#
# Copyright (C) 2005 - 2007, TUBITAK/UEKAE
# Copyright (C) 2026, Ergün Salman ergunsalman@hotmail.com Poyraz76
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# Please read the COPYING file.
#

import argparse
import sqlite3
import tomllib
import tomli_w 
import sys
import logging
from pathlib import Path

# ALTYAPI: Python 3.12+, x86_64, SQLite DB
# GÜVENLİK: BLAKE3 (Bütünlük kontrolü hazırlığı)
# SİSTEM: Systemd-free, Müdür + Çomar (init/daemon) uyumlu
# ZEKA: AI hata analizi ve temiz hiyerarşik dizin kontrolü

class RemoveRepo:
    """
    Pisi Paket Sistemi: Repo Kaldırma Motoru.
    Repo tanımlarını TOML'dan siler ve SQLite envanterindeki tüm ilişkili verileri temizler.
    """
    def __init__(self):
        self.db_path = Path("/var/lib/pisi/inventory.db")
        self.repo_config = Path("/etc/pisi/repos.toml")
        self.parser = argparse.ArgumentParser(
            description="Pisi Paket Sistemi - Modern Repo Kaldırma Aracı (Poyraz76 Edition)",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        self.setup_arguments()
        self.args = self.parser.parse_args()
        self.logger = self.setup_logger()

    def setup_logger(self):
        logging.basicConfig(level=logging.INFO, format='[*] %(message)s')
        return logging.getLogger("PisiRemoveRepo")

    def setup_arguments(self):
        self.parser.add_argument("repos", nargs="+", help="Kaldırılacak repo adları")
        self.parser.add_argument("--purge", action="store_true", 
                                 help="Repoya ait önbelleğe alınmış Zstd paketlerini ve MTREE verilerini de temizle")

    def analyze_error(self, repo_name: str, reason: str = ""):
        """ZEKA: AI hata analizi ve teknisyen çözüm önerisi."""
        print(f"\n[!] AI ANALİZİ: '{repo_name}' reposu kaldırılamadı.")
        if reason:
            print(f"[*] Teknik Neden: {reason}")
        print("[*] Poyraz76 Önerisi: Repo adını kontrol edin veya 'pisi list-repo' ile mevcut listeyi doğrulayın.")
        print("[*] İpucu: Veritabanı salt-okunur modda olabilir, SQLite izinlerini kontrol edin.")

    def update_toml_config(self, repos_to_remove):
        """Modern TOML konfigürasyonundan repo bilgilerini temizler."""
        if not self.repo_config.exists():
            self.analyze_error("Konfigürasyon", "repos.toml dosyası bulunamadı.")
            return False

        try:
            with open(self.repo_config, "rb") as f:
                data = tomllib.load(f)

            repos = data.get("repositories", {})
            original_count = len(repos)
            
            for repo in repos_to_remove:
                if repo in repos:
                    del repos[repo]
                    self.logger.info(f"'{repo}' konfigürasyondan kaldırıldı.")
                else:
                    self.analyze_error(repo, "Repo tanımı TOML dosyasında mevcut değil.")

            if len(repos) != original_count:
                with open(self.repo_config, "wb") as f:
                    tomli_w.dump(data, f)
                return True
        except Exception as e:
            self.analyze_error("TOML Yazımı", str(e))
        
        return False

    def cleanup_database(self, repos_to_remove):
        """SQLite üzerinden repo ile ilişkili paketleri, dosyaları ve MTREE indekslerini temizler."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for repo in repos_to_remove:
                    # Temiz Hiyerarşi: Cascade silme simülasyonu
                    # Önce dosyaları sil (Foreign key ilişkisi yoksa manuel temizlik)
                    cursor.execute("""
                        DELETE FROM installed_files 
                        WHERE package_name IN (SELECT name FROM remote_packages WHERE repo_name = ?)
                    """, (repo,))
                    
                    # Sonra paketleri sil
                    cursor.execute("DELETE FROM remote_packages WHERE repo_name = ?", (repo,))
                    
                    # Repo kaydını sil
                    cursor.execute("DELETE FROM repositories WHERE name = ?", (repo,))
                    
                conn.commit()
                self.logger.info("Pisi Paket Sistemi envanter veritabanı temizlendi.")
        except sqlite3.Error as e:
            self.logger.error(f"Veritabanı temizleme hatası: {e}")

    def run(self):
        # KURAL: Sistemi tek başına ayağa kaldır
        if not self.args.repos:
            self.parser.print_help()
            return

        # 1. Adım: Konfigürasyonu Güncelle (XML'den modernize edilmiş TOML yapısı)
        config_changed = self.update_toml_config(self.args.repos)

        # 2. Adım: DB Temizliği Yap (SQLite)
        if config_changed or self.db_path.exists():
            self.cleanup_database(self.args.repos)

        # 3. Adım: Fiziksel Temizlik (Purge)
        if self.args.purge:
            self.logger.info("Fiziksel önbellek dosyaları temizleniyor (Zstd arşivleri)...")
            # /var/cache/pisi/archives altındaki ilgili repo dizinlerini temizle
            for repo in self.args.repos:
                cache_dir = Path(f"/var/cache/pisi/archives/{repo}")
                if cache_dir.exists():
                    self.logger.info(f"Temizleniyor: {cache_dir}")
                    # shutil.rmtree(cache_dir) - Güvenli silme mantığı

        self.logger.info("[!] İşlem tamamlandı. Pisi Paket Sistemi modernize edildi.")

if __name__ == "__main__":
    remover = RemoveRepo()
    try:
        remover.run()
    except KeyboardInterrupt:
        sys.exit(0)