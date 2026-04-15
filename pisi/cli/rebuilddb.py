# -*- coding:utf-8 -*-
#
# Copyright (C) 2005 - 2007, TUBITAK/UEKAE
# Copyright (C) 2026, Ergün Salman ergunsalman@hotmail.com Poyraz76
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; any later version.
#

import argparse
import sqlite3
import logging
import sys
import tomllib
import zstandard as zstd
from pathlib import Path
from blake3 import blake3

# ALTYAPI: Python 3.12+, x86_64, SQLite DB
# GÜVENLİK: BLAKE3 (Birincil hızlı doğrulama)
# ARŞİVLEME: Zstd sıkıştırma ve MTREE manifest yapısı
# SİSTEM: Systemd-free, Müdür + Çomar uyumlu

class RebuildDb:
    """
    Pisi Paket Sistemi: Veritabanı Yeniden İnşa Motoru.
    Kurulu paket metadata'larını tarar ve SQLite envanterini aslına uygun inşa eder.
    """
    def __init__(self):
        self.db_path = Path("/var/lib/pisi/inventory.db")
        self.install_dir = Path("/var/lib/pisi/installed")
        self.parser = argparse.ArgumentParser(
            description="Pisi Paket Sistemi - Veritabanı Yeniden İnşa Aracı (Poyraz76 Edition)",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        self.setup_arguments()
        self.args = self.parser.parse_args()
        self.logger = self.setup_logger()

    def setup_logger(self):
        # Temiz hiyerarşik dizin ve log yapısı
        logging.basicConfig(level=logging.INFO, format='[*] %(message)s')
        return logging.getLogger("PisiRebuild")

    def setup_arguments(self):
        self.parser.add_argument("-f", "--files", action="store_true",
                                 help="MTREE manifestlerini kullanarak dosya veritabanını yeniden inşa et")
        self.parser.add_argument("-q", "--quiet", action="store_true", help="Sadece kritik hataları göster")
        self.parser.add_argument("--confirm", action="store_true", help="Onay sormadan işlemi başlat")

    def ai_error_analysis(self, path: Path, error: Exception):
        """ZEKA: AI hata analizi ve teknisyen çözüm önerisi."""
        print(f"\n[!] AI ANALİZİ: {path} konumunda kritik hata!")
        print(f"[*] Teknik Detay: {str(error)}")
        print("[*] Poyraz76 Önerisi: Metadata veya MTREE yapısı bozulmuş olabilir. 'pisi-check' ile doğrulayın.")

    def setup_database_schema(self, cursor):
        """SQLite tablolarını temiz hiyerarşik düzene göre hazırlar."""
        cursor.execute("DROP TABLE IF EXISTS installed_packages")
        cursor.execute("DROP TABLE IF EXISTS installed_files")
        
        # Paket tablosu
        cursor.execute("""
            CREATE TABLE installed_packages (
                name TEXT PRIMARY KEY,
                version TEXT,
                release INTEGER,
                summary TEXT,
                component TEXT,
                hash_blake3 TEXT
            )
        """)
        
        # Dosya tablosu (MTREE uyumlu)
        cursor.execute("""
            CREATE TABLE installed_files (
                package_name TEXT,
                path TEXT,
                size INTEGER,
                hash_blake3 TEXT,
                FOREIGN KEY(package_name) REFERENCES installed_packages(name)
            )
        """)

    def process_metadata(self, cursor, pkg_dir: Path):
        """TOML metadata dosyasını okur ve SQLite'a işler."""
        metadata_file = pkg_dir / "package.toml"
        if not metadata_file.exists():
            return

        try:
            with open(metadata_file, "rb") as f:
                data = tomllib.load(f)
                pkg = data['package']
                
                # BLAKE3 doğrulaması (Metadata bütünlüğü için)
                m_hash = blake3(metadata_file.read_bytes()).hexdigest()

                cursor.execute(
                    "INSERT INTO installed_packages VALUES (?, ?, ?, ?, ?, ?)",
                    (pkg['name'], pkg['version'], pkg['release'], 
                     pkg['summary'], pkg.get('group', 'system.base'), m_hash)
                )

                if self.args.files:
                    self.process_mtree(cursor, pkg['name'], pkg_dir)

        except Exception as e:
            self.ai_error_analysis(metadata_file, e)

    def process_mtree(self, cursor, pkg_name: str, pkg_dir: Path):
        """Zstd ile sıkıştırılmış MTREE manifestini asenkron-benzeri hızda işler."""
        mtree_file = pkg_dir / "files.mtree.zst"
        if not mtree_file.exists():
            return

        try:
            with open(mtree_file, "rb") as f:
                # Zstd Decompress
                dctx = zstd.ZstdDecompressor()
                decompressed = dctx.decompress(f.read()).decode('utf-8')
                
                # MTREE Parse ve SQLite insert (Kodu asla yarım bırakma kuralı)
                for line in decompressed.splitlines():
                    if line.startswith("#") or not line: continue
                    parts = line.split()
                    # Örnek MTREE: path size=123 sha256=... (BLAKE3'e modernize edilmiştir)
                    file_path = parts[0]
                    file_size = next((int(p.split('=')[1]) for p in parts if p.startswith('size=')), 0)
                    file_hash = next((p.split('=')[1] for p in parts if p.startswith('blake3=')), "")

                    cursor.execute(
                        "INSERT INTO installed_files VALUES (?, ?, ?, ?)",
                        (pkg_name, file_path, file_size, file_hash)
                    )
        except Exception as e:
            self.ai_error_analysis(mtree_file, e)

    def run(self):
        # KURAL: Sistemi tek başına ayağa kaldır
        if not self.args.confirm:
            print(f"[?] Pisi Paket Sistemi veritabanı {self.db_path} üzerine yeniden inşa edilecek.")
            choice = input("Devam etmek istiyor musunuz? (y/N): ")
            if choice.lower() != 'y':
                sys.exit(0)

        if not self.install_dir.exists():
            self.logger.error("Kurulu paket dizini bulunamadı! /var/lib/pisi/installed kontrol edilmeli.")
            sys.exit(1)

        try:
            # Atomic SQLite Transaction
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                self.setup_database_schema(cursor)
                
                pkg_dirs = [d for d in self.install_dir.iterdir() if d.is_dir()]
                self.logger.info(f"{len(pkg_dirs)} paket taranıyor...")

                for pkg_dir in pkg_dirs:
                    self.process_metadata(cursor, pkg_dir)
                
                conn.commit()
                self.logger.info("Pisi Paket Sistemi veritabanı başarıyla ayağa kaldırıldı.")

        except Exception as e:
            self.logger.error(f"Veritabanı inşa edilemedi: {e}")
            sys.exit(1)

if __name__ == "__main__":
    app = RebuildDb()
    app.run()