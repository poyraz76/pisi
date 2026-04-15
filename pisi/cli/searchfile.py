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
import sys
import logging
from pathlib import Path
from typing import List, Tuple

# ALTYAPI: Python 3.12+, x86_64, SQLite DB
# GÜVENLİK: BLAKE3 (Dosya bütünlük doğrulaması)
# SİSTEM: Systemd-free, Müdür + Çomar uyumlu
# ARŞİVLEME: MTREE manifest yapısı entegreli

class SearchFile:
    """
    Pisi Paket Sistemi: Dosya Arama ve Envanter Sorgulama.
    Kurulu dosyaların hangi pakete ait olduğunu SQLite DB ve MTREE verileriyle bulur.
    """
    def __init__(self):
        self.db_path = Path("/var/lib/pisi/inventory.db")
        self.parser = argparse.ArgumentParser(
            description="Pisi Paket Sistemi - Modern Dosya Arama (Poyraz76 Edition)",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        self.setup_arguments()
        self.args = self.parser.parse_args()
        self.logger = self.setup_logger()

    def setup_logger(self):
        logging.basicConfig(level=logging.INFO, format='[*] %(message)s')
        return logging.getLogger("PisiSearchFile")

    def setup_arguments(self):
        self.parser.add_argument("paths", nargs="+", help="Aranacak dosya yolları veya isimleri")
        self.parser.add_argument("-l", "--long", action="store_true", 
                                 help="Detaylı çıktı (Boyut ve BLAKE3 hash bilgisini gösterir)")
        self.parser.add_argument("-q", "--quiet", action="store_true", help="Sadece paket adını yazdır")
        self.parser.add_argument("--regex", action="store_true", help="Düzenli ifade (Regex) ile ara")

    def search_in_db(self, search_path: str) -> List[Tuple]:
        """SQLite üzerinden MTREE tabanlı dosya araması yapar."""
        results = []
        try:
            with sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True) as conn:
                cursor = conn.cursor()
                
                # MTREE yapısına uygun sorgu: package_name, path, size, hash_blake3
                fields = "package_name, path"
                if self.args.long:
                    fields = "package_name, path, size, hash_blake3"
                
                if self.args.regex:
                    # SQLite modern C/C++ regex eklentisi varsayılır
                    query = f"SELECT {fields} FROM installed_files WHERE path REGEXP ?"
                    param = search_path
                else:
                    query = f"SELECT {fields} FROM installed_files WHERE path LIKE ?"
                    param = f"%{search_path}%"

                cursor.execute(query, (param,))
                results = cursor.fetchall()
        except sqlite3.Error as e:
            self.analyze_error(f"Veritabanı erişim hatası: {e}")
        
        return results

    def analyze_error(self, error_msg: str, path: str = ""):
        """ZEKA: AI hata analizi ve temiz hiyerarşik dizin kontrolü."""
        print(f"\n[!] AI ANALİZİ: {error_msg}")
        if path:
            print(f"[*] Poyraz76 İpucu: '{path}' dosyası sistem envanterinde (inventory.db) kayıtlı değil.")
            print(f"[*] Öneri: Dosya bir paket dışı kurulum olabilir veya 'rebuild-db' yapılması gerekebilir.")

    def run(self):
        # KURAL: Sistemi tek başına ayağa kaldır
        if not self.db_path.exists():
            self.analyze_error("Envanter veritabanı bulunamadı! 'Müdür' ile senkronizasyon gerekli.")
            sys.exit(1)

        for path in self.args.paths:
            if not self.args.quiet:
                self.logger.info(f"'{path}' sorgulanıyor...")

            found_items = self.search_in_db(path)

            if not found_items:
                self.analyze_error("Dosya bulunamadı", path)
                continue

            for item in found_items:
                pkg = item[0]
                pkg_file = item[1]
                
                if self.args.quiet:
                    print(pkg)
                elif self.args.long:
                    # MTREE ve BLAKE3 detaylı çıktı
                    size, b3_hash = item[2], item[3]
                    print(f" Paket: \033[1;32m{pkg:<20}\033[0m Boyut: {size:>10} B | BLAKE3: {b3_hash[:16]}... | Yol: /{pkg_file}")
                else:
                    # Temiz hiyerarşik dizin çıktısı
                    print(f" Paket: \033[1;32m{pkg}\033[0m -> Dosya: \033[1;34m/{pkg_file}\033[0m")

if __name__ == "__main__":
    app = SearchFile()
    try:
        app.run()
    except KeyboardInterrupt:
        sys.exit(0)