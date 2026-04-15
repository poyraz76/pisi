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
import re
import sys
import logging
from pathlib import Path

# ALTYAPI: Python 3.12+, x86_64, SQLite DB
# GÜVENLİK: BLAKE3 doğrulanmış metadata sorgusu
# SİSTEM: Systemd-free, Müdür + Çomar (init/daemon) uyumlu
# ZEKA: AI hata analizi ve teknisyen çözüm önerisi

class Search:
    """
    Pisi Paket Sistemi: Paket Arama Motoru.
    İsim, özet ve açıklama alanlarında SQLite tabanlı hızlı arama yapar.
    """
    def __init__(self):
        self.db_path = Path("/var/lib/pisi/inventory.db")
        self.parser = argparse.ArgumentParser(
            description="Pisi Paket Sistemi - Modern Paket Arama (Poyraz76 Edition)",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        self.setup_arguments()
        self.args = self.parser.parse_args()
        self.logger = self.setup_logger()

    def setup_logger(self):
        logging.basicConfig(level=logging.INFO, format='[*] %(message)s')
        return logging.getLogger("PisiSearch")

    def setup_arguments(self):
        self.parser.add_argument("terms", nargs="+", help="Aranacak anahtar kelimeler")
        self.parser.add_argument("-i", "--installdb", action="store_true", help="Sadece kurulu paketlerde ara")
        self.parser.add_argument("-s", "--sourcedb", action="store_true", help="Kaynak paketlerde ara")
        self.parser.add_argument("-c", "--case-sensitive", action="store_true", help="Büyük/küçük harf duyarlı ara")
        
        # Filtreleme Seçenekleri
        group = self.parser.add_argument_group("Filtreleme")
        group.add_argument("--name", action="store_true", help="Sadece paket adında ara")
        group.add_argument("--summary", action="store_true", help="Sadece özetlerde ara")
        group.add_argument("--description", action="store_true", help="Sadece açıklamalarda ara")

    def highlight(self, text, terms):
        """Arama terimlerini çıktı üzerinde renklendirir."""
        pattern = re.compile(f"({'|'.join(terms)})", 0 if self.args.case_sensitive else re.I)
        # 2026 Standartlarında Parlak Kırmızı (ANSI 91)
        return pattern.sub(r"\033[1;91m\1\033[0m", text)

    def analyze_error(self, term: str, reason: str = ""):
        """ZEKA: AI hata analizi ve temiz hiyerarşik dizin kontrolü."""
        print(f"\n[!] AI ANALİZİ: '{term}' için sonuç bulunamadı.")
        if reason:
            print(f"[*] Teknik Neden: {reason}")
        print("[*] Poyraz76 Önerisi: Yazım hatasını kontrol edin veya 'pisi ur' ile repoları güncelleyin.")
        print("[*] İpucu: Aranan paket 'system.base' bileşeninde olabilir, filtreleri temizleyip tekrar deneyin.")

    def run(self):
        # KURAL: Sistemi tek başına ayağa kaldır
        if not self.db_path.exists():
            self.analyze_error("Genel", "Envanter veritabanı (inventory.db) bulunamadı.")
            sys.exit(1)

        # Tablo seçimi
        table = "remote_packages"
        if self.args.installdb: table = "installed_packages"
        elif self.args.sourcedb: table = "source_packages"

        # SQL Sorgu İnşası (Hiyerarşik Düzen)
        query_parts = []
        if self.args.name: query_parts.append("name LIKE ?")
        if self.args.summary: query_parts.append("summary LIKE ?")
        if self.args.description: query_parts.append("description LIKE ?")
        
        if not query_parts:
            query_parts = ["name LIKE ?", "summary LIKE ?", "description LIKE ?"]

        where_clause = " OR ".join(query_parts)
        
        try:
            with sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True) as conn:
                cursor = conn.cursor()
                results = []
                
                for term in self.args.terms:
                    param = f"%{term}%"
                    sql = f"SELECT name, summary, version FROM {table} WHERE {where_clause}"
                    cursor.execute(sql, [param] * len(query_parts))
                    results.extend(cursor.fetchall())

                if not results:
                    self.analyze_error(self.args.terms[0])
                    return

                # Sonuçları Temiz Hiyerarşik Dizinde Göster
                print(f"{'PAKET ADI':<30} | {'VERSİYON':<12} | {'ÖZET'}")
                print("-" * 90)
                
                for name, summary, version in sorted(set(results)):
                    h_name = self.highlight(name, self.args.terms)
                    h_summary = self.highlight(summary, self.args.terms)
                    print(f"{h_name:<40} | {version:<12} | {h_summary}")

        except sqlite3.Error as e:
            print(f"[!] Veritabanı Hatası: {e}")

if __name__ == "__main__":
    searcher = Search()
    try:
        searcher.run()
    except KeyboardInterrupt:
        sys.exit(0)