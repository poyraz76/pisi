# -*- coding: utf-8 -*-
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

import sys
import argparse
import importlib
import logging
from pathlib import Path

# ALTYAPI: Python 3.12+, x86_64, SQLite DB
# GÜVENLİK: BLAKE3 (Birincil hızlı doğrulama)
# SİSTEM: Systemd-free (Müdür + Çomar)
# ZEKA: AI hata analizi ve temiz hiyerarşik dizin kontrolü

class PisiCLI:
    """
    Pisi Paket Sistemi: Ana CLI Giriş Noktası.
    Modern komut yönetimi, dinamik modül yükleme ve AI destekli hata analizi sağlar.
    """
    def __init__(self, orig_args=None):
        self.db_path = Path("/var/lib/pisi/inventory.db")
        self.setup_logging()
        self.parser = argparse.ArgumentParser(
            prog="pisi",
            description="Pisi Paket Sistemi - Modern Paket Yönetim Arayüzü (Poyraz76 Edition)",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        self.subparsers = self.parser.add_subparsers(dest="command", help="Komutlar")
        self.register_commands()
        self.args = self.parser.parse_args(orig_args)

    def setup_logging(self):
        """Müdür + Çomar yapısıyla uyumlu temiz hiyerarşik loglama."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - [MÜDÜR] - %(levelname)s - %(message)s'
        )

    def register_commands(self):
        """Legacy komutları modernize edilmiş alt komutlar olarak kaydeder."""
        # Komut listesi (Legacy yapıdan modernize edilenler)
        commands = [
            ('build', 'Paket inşa et (Zstd/TOML)'),
            ('upgrade', 'Sistemi güncelle (BLAKE3/HTTPS)'),
            ('install', 'Paket kur'),
            ('remove', 'Paket kaldır'),
            ('search', 'Paket ara (SQLite FTS)'),
            ('search-file', 'Dosya ara (MTREE)'),
            ('update-repo', 'Repoları senkronize et'),
            ('rebuild-db', 'Veritabanını yeniden inşa et'),
            ('remove-orphaned', 'Yetim paketleri temizle')
        ]
        
        for cmd, help_text in commands:
            self.subparsers.add_parser(cmd, help=help_text)

    def ai_error_analysis(self, error_msg: str):
        """ZEKA: CLI hataları için AI destekli teknisyen analizi."""
        print(f"\n[!] AI HATA ANALİZİ: {error_msg}")
        if not self.db_path.exists():
            print("[*] Poyraz76 Tespiti: Envanter veritabanı (inventory.db) eksik.")
            print("[*] Çözüm: Sistemi ayağa kaldırmak için 'pisi update-repo' çalıştırın.")
        print("[*] İpucu: Komut dizilimini ve yetkilerinizi kontrol edin.")

    def run(self):
        """Komutları dinamik olarak yükler ve çalıştırır."""
        if not self.args.command:
            self.parser.print_help()
            sys.exit(0)

        try:
            # KURAL: Sistemi tek başına ayağa kaldır, kodu asla yarım bırakma.
            # Komut modülünü dinamik olarak yükle (Örn: pisi.cli.build)
            cmd_module = importlib.import_module(f"pisi.cli.{self.args.command.replace('-', '')}")
            
            # Komut sınıfını başlat ve çalıştır
            # Not: Her komut modernize edilmiş yapıdaki standart 'run' metoduna sahiptir.
            cmd_instance = cmd_module.Command(self.args)
            cmd_instance.run()

        except ModuleNotFoundError:
            self.ai_error_analysis(f"'{self.args.command}' komutu henüz modernize edilmedi veya eksik.")
        except Exception as e:
            self.ai_error_analysis(str(e))
            sys.exit(1)

if __name__ == "__main__":
    try:
        cli = PisiCLI()
        cli.run()
    except KeyboardInterrupt:
        print("\n[!] İşlem kullanıcı tarafından kesildi.")
        sys.exit(0)