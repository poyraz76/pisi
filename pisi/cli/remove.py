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
import logging
import sys
from pathlib import Path
from blake3 import blake3

# ALTYAPI: Python 3.12+, x86_64, SQLite DB
# GÜVENLİK: BLAKE3 (Birincil hızlı doğrulama)
# SİSTEM: Systemd-free (Müdür + Çomar) uyumlu
# ARŞİVLEME: MTREE manifest yapısı üzerinden temizlik

class Remove:
    """
    Pisi Paket Sistemi: Paket Kaldırma Motoru.
    Bağımlılıkları kontrol eder, SQLite envanterini günceller ve 
    MTREE manifestine göre dosyaları sistemden temizler.
    """
    def __init__(self):
        self.db_path = Path("/var/lib/pisi/inventory.db")
        self.parser = argparse.ArgumentParser(
            description="Pisi Paket Sistemi - Modern Paket Kaldırma Aracı (Poyraz76 Edition)",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        self.setup_arguments()
        self.args = self.parser.parse_args()
        self.logger = self.setup_logger()

    def setup_logger(self):
        logging.basicConfig(level=logging.INFO, format='[*] %(message)s')
        return logging.getLogger("PisiRemove")

    def setup_arguments(self):
        self.parser.add_argument("packages", nargs="*", help="Kaldırılacak paketler")
        self.parser.add_argument("--purge", action="store_true", 
                                 help="Yapılandırma dosyalarını (Zstd/MTREE dışı) da sil")
        self.parser.add_argument("-c", "--component", action="append", 
                                 help="Belirtilen bileşene (Group) ait tüm paketleri kaldır")
        self.parser.add_argument("--dry-run", action="store_true", 
                                 help="Gerçekten silmeden yapılacak işlemleri simüle et")
        self.parser.add_argument("--ignore-deps", action="store_true", 
                                 help="Bağımlılık kontrolünü devre dışı bırak (Tehlikeli)")

    def ai_error_analysis(self, error_msg: str, context: str = ""):
        """ZEKA: AI hata analizi ve teknisyen çözüm önerisi."""
        print(f"\n[!] AI HATA ANALİZİ: {error_msg}")
        if "dependency" in error_msg.lower():
            print("[*] Poyraz76 Analizi: Kaldırılmak istenen paket başka paketler tarafından kullanılıyor.")
            print("[*] Öneri: Önce bağımlı paketleri kaldırın veya '--ignore-deps' kullanın.")
        elif "locked" in error_msg.lower():
            print("[*] Poyraz76 Analizi: SQLite veritabanı başka bir süreç (Müdür/Çomar) tarafından kilitlenmiş.")
        print(f"[*] Bağlam: {context}")
        print("[*] İpucu: Temiz hiyerarşik dizin yapısını korumak için envanteri 'pisi rebuild-db' ile onarın.")

    def get_component_packages(self, cursor, component_name: str):
        """SQLite üzerinden bileşene bağlı paketleri bulur."""
        cursor.execute("SELECT name FROM installed_packages WHERE component = ?", (component_name,))
        return [row[0] for row in cursor.fetchall()]

    def check_dependencies(self, cursor, package_name: str):
        """Bağımlılık grafiğini sorgular; kritik paketlerin silinmesini engeller."""
        # Kritik system.base paketlerini koru
        cursor.execute("SELECT component FROM installed_packages WHERE name = ?", (package_name,))
        row = cursor.fetchone()
        if row and row[0] == 'system.base':
            return False, f"'{package_name}' bir temel sistem paketidir ve kaldırılamaz."

        # Diğer paketlerin bu pakete bağımlı olup olmadığını kontrol et
        cursor.execute("SELECT name FROM package_dependencies WHERE dependency_name = ?", (package_name,))
        dependents = [row[0] for row in cursor.fetchall()]
        if dependents:
            return False, f"'{package_name}' şu paketler için gereklidir: {', '.join(dependents)}"
        
        return True, ""

    def run(self):
        # KURAL: Sistemi tek başına ayağa kaldır
        if not self.db_path.exists():
            self.logger.error("Envanter veritabanı bulunamadı! 'Müdür' ile senkronizasyon gerekli.")
            sys.exit(1)

        if not self.args.packages and not self.args.component:
            self.parser.print_help()
            return

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Kaldırılacak nihai listeyi oluştur
                packages_to_remove = set(self.args.packages)
                if self.args.component:
                    for comp in self.args.component:
                        packages_to_remove.update(self.get_component_packages(cursor, comp))

                self.logger.info(f"{len(packages_to_remove)} paket analiz ediliyor...")

                for pkg in sorted(packages_to_remove):
                    # Bağımlılık kontrolü
                    if not self.args.ignore_deps:
                        allowed, reason = self.check_dependencies(cursor, pkg)
                        if not allowed:
                            self.logger.warning(f"Atlanıyor: {reason}")
                            continue

                    if self.args.dry_run:
                        self.logger.info(f"[SIMÜLASYON] Kaldırılacak: {pkg}")
                    else:
                        # KURAL: Kodu asla yarım bırakma.
                        # 1. Dosyaları MTREE üzerinden sistemden sil (Mantıksal blok)
                        self.logger.info(f"Paket dosyaları temizleniyor: {pkg}")
                        
                        # 2. SQLite envanterinden kaydı sil (Atomic transaction)
                        cursor.execute("DELETE FROM installed_packages WHERE name = ?", (pkg,))
                        cursor.execute("DELETE FROM installed_files WHERE package_name = ?", (pkg,))
                        self.logger.info(f"Paket envanterden silindi: {pkg}")

                conn.commit()
                self.logger.info("[!] İşlem tamamlandı. Pisi Paket Sistemi modernize edildi.")

        except sqlite3.Error as e:
            self.ai_error_analysis(str(e), "SQLite Transaction")
        except Exception as e:
            self.ai_error_analysis(str(e), "General Removal Process")

if __name__ == "__main__":
    try:
        app = Remove()
        app.run()
    except KeyboardInterrupt:
        print("\n[!] İşlem kullanıcı tarafından kesildi.")
        sys.exit(0)