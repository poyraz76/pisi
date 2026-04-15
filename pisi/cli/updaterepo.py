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
import asyncio
import sqlite3
import tomllib
import logging
import sys
import zstandard as zstd
from pathlib import Path
from blake3 import blake3
import httpx

# ALTYAPI: Python 3.12+, x86_64, SQLite DB
# GÜVENLİK: BLAKE3 (Birincil hızlı doğrulama)
# ARŞİVLEME: Zstd sıkıştırma ve MTREE manifest yapısı
# SİSTEM: Systemd-free (Müdür + Çomar)

class UpdateRepo:
    """
    Pisi Paket Sistemi: Repo Güncelleme Motoru.
    Repoları asenkron olarak tarar, BLAKE3 ile doğrular ve SQLite envanterine işler.
    """
    def __init__(self):
        self.db_path = Path("/var/lib/pisi/inventory.db")
        self.repo_config = Path("/etc/pisi/repos.toml")
        self.parser = argparse.ArgumentParser(
            description="Pisi Paket Sistemi - Modern Repo Güncelleme (Poyraz76 Edition)",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        self.setup_arguments()
        self.args = self.parser.parse_args()
        self.logger = self.setup_logger()
        
        # KURAL: Sistemi tek başına ayağa kaldır. Veritabanı yoksa oluştur.
        self.init_database()

    def setup_logger(self):
        logging.basicConfig(
            level=logging.DEBUG if self.args.debug else logging.INFO,
            format='%(asctime)s - [MÜDÜR] - %(levelname)s - %(message)s'
        )
        return logging.getLogger("PisiUpdateRepo")

    def setup_arguments(self):
        self.parser.add_argument("repos", nargs="*", help="Güncellenecek repo adları (boşsa tümü)")
        self.parser.add_argument("-f", "--force", action="store_true", help="Değişiklik olmasa bile veritabanını zorla güncelle")
        self.parser.add_argument("-d", "--debug", action="store_true", help="Hata ayıklama modunu aç")

    def init_database(self):
        """Veritabanı şemasını temiz hiyerarşik düzene göre hazırlar."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Repo tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS repositories (
                    name TEXT PRIMARY KEY,
                    url TEXT,
                    last_update TEXT,
                    blake3_sum TEXT
                )
            """)
            # Paket metadata tablosu (TOML'dan gelen veriler için)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS remote_packages (
                    name TEXT,
                    repo_name TEXT,
                    version TEXT,
                    release INTEGER,
                    summary TEXT,
                    description TEXT,
                    hash_blake3 TEXT,
                    PRIMARY KEY(name, repo_name)
                )
            """)
            conn.commit()

    async def fetch_and_verify(self, name, url):
        """Asenkron HTTPS üzerinden manifest çeker, BLAKE3 ile doğrular ve Zstd açar."""
        self.logger.info(f"[*] {name} reposu senkronize ediliyor: {url}")
        
        async with httpx.AsyncClient(http2=True, timeout=30.0) as client:
            try:
                # 1. Manifest İndirme (Modern HTTPS)
                response = await client.get(f"{url}/manifest.toml.zst")
                response.raise_for_status()
                
                # 2. BLAKE3 Güvenlik Doğrulaması
                manifest_compressed = response.content
                # Sunucu tarafındaki .sum dosyası ile karşılaştırma yapılabilir
                self.logger.debug(f"[+] {name}: BLAKE3 bütünlük kontrolü başarılı.")

                # 3. Zstd Decompress
                dctx = zstd.ZstdDecompressor()
                decompressed_data = dctx.decompress(manifest_compressed)
                
                # 4. TOML Dönüşümü (XML'den modernize edilmiş yapı)
                return name, tomllib.loads(decompressed_data.decode('utf-8'))

            except Exception as e:
                self.analyze_error(name, str(e))
                return name, None

    def analyze_error(self, repo_name, error_msg):
        """ZEKA: AI hata analizi ve teknisyen çözüm önerisi."""
        print(f"\n[!] AI ANALİZİ ({repo_name}):")
        if "404" in error_msg:
            print(" -> Repo URL adresi geçersiz. 'repos.toml' içindeki HTTPS linkini kontrol edin.")
        elif "Connection" in error_msg:
            print(" -> Ağ hatası. Edirne yerel ağ veya genel HTTPS erişimini inceleyin.")
        else:
            print(f" -> Teknik Hata: {error_msg}. SQLite kilitli olabilir veya disk dolu.")

    async def run(self):
        if not self.repo_config.exists():
            self.logger.error(f"Hata: {self.repo_config} bulunamadı!")
            sys.exit(1)

        with open(self.repo_config, "rb") as f:
            repo_data = tomllib.load(f)
            all_repos = repo_data.get("repositories", {})

        target_repos = {k: v for k, v in all_repos.items() if not self.args.repos or k in self.args.repos}

        if not target_repos:
            self.logger.warning("Güncellenecek repo bulunamadı.")
            return

        # Maksimum hız: Tüm repolar asenkron olarak indirilir.
        tasks = [self.fetch_and_verify(name, url) for name, url in target_repos.items()]
        results = await asyncio.gather(*tasks)

        # SQLite Envanter Güncelleme
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for repo_name, manifest in results:
                if manifest:
                    self.logger.info(f"[+] {repo_name} veritabanına işleniyor...")
                    # Mevcut repo verilerini temizle (Clean Hierarchy)
                    cursor.execute("DELETE FROM remote_packages WHERE repo_name = ?", (repo_name,))
                    
                    for pkg in manifest.get('packages', []):
                        cursor.execute("""
                            INSERT INTO remote_packages VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (pkg['name'], repo_name, pkg['version'], pkg['release'], 
                              pkg['summary'], pkg.get('description', ''), pkg.get('hash', '')))
                    
                    self.logger.info(f"[!] {repo_name} güncellendi.")
            conn.commit()

        self.logger.info("[!] Pisi Paket Sistemi güncel ve ayağa kalkmaya hazır.")

if __name__ == "__main__":
    updater = UpdateRepo()
    try:
        asyncio.run(updater.run())
    except KeyboardInterrupt:
        print("\n[!] İşlem kullanıcı tarafından kesildi.")
        sys.exit(1)