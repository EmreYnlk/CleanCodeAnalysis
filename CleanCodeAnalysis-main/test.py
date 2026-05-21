import sys
import os
import json
import time
import math
#sys, json ve time kütüphaneleri kullanılmamaktadır 

class HariciSistem:
    def __init__(self):
        self.ip_adresi = "192.168.1.100"
        self.port = 8080
        self.baglanti_tipi = "SSL"
        self.maks_deneme = 5
        self.zaman_asimi = 30

class VeriAnalizMotoru:
    """
    Bu sınıf bir 'God Class' örneğidir. Hem çok büyüktür hem de içinde tanımlanan metotlar 
    sınıfın üye değişkenlerini ortaklaşa kullanmadığı için LCOM (Lack of Cohesion of Methods) skoru yüksektir.
    """
    def __init__(self):
        self.ana_veri = []
        self.durum = "Hazır"
        self.hata_sayisi = 0

    def veri_yukle(self, veri):
        self.ana_veri = veri
        self.durum = "Yüklendi"

    def karmasik_hesaplama_metodu(self, veri_listesi):
        """
        DR-04: Deep Nesting (Aşırı Dallanma) İhlali.
        Bu metot iç içe 4 seviyeden fazla derinliğe sahiptir ve okunabilirliği düşüktür.
        Ayrıca 25 satırdan uzun olduğu için Long Method uyarısı alacaktır.
        """
        kullanilmayan_degisken = 100 # UYARI: Dead Code (Kullanılmayan Yerel Değişken)
        toplam_sonuc = 0
        
        for veri in veri_listesi:
            if veri is not None:
                if isinstance(veri, int) or isinstance(veri, float):
                    if veri > 0:
                        for carpan in range(1, 6):
                            if carpan % 2 != 0:
                                # Halstead metriklerini artıracak karmaşık işlemler
                                deger = math.pow(veri, 2) * math.sqrt(carpan) / (carpan + 1)
                                toplam_sonuc += deger
                                print("Ara Değer Hesaplanıyor:", deger)
                                
        self.durum = "Hesaplama Tamamlandı"
        return toplam_sonuc

    def kullaniciyi_sisteme_kaydet(self, ad, soyad, eposta, telefon, sifre, adres, rol, yetki_seviyesi):
        """
        DR-05: Too Many Arguments (Aşırı Parametre) İhlali.
        Bir metodun temiz kod prensiplerine göre en fazla 4 parametre alması önerilir. Bu metot ise 8 parametre almaktadır.
        """
        kullanici_kartı = {
            "ad": ad,
            "soyad": soyad,
            "eposta": eposta,
            "tel": telefon,
            "sifre": sifre,
            "adres": adres,
            "rol": rol,
            "yetki": yetki_seviyesi
        }
        self.ana_veri.append(kullanici_kartı)
        return True

    def baglantiyi_test_et(self, sistem):
        """
        Feature Envy (Özellik Kıskançlığı) İhlali.
        Bu metot kendi sınıfının (VeriAnalizMotoru) üye değişkenleri yerine, parametre olarak gelen 
        'sistem' (HariciSistem) nesnesinin üye değişkenlerine aşırı erişim sağlamaktadır.
        """
        print("Sistem Bilgileri Okunuyor...")
        # Harici nesneye ait değişkenlerin yoğun okunması/yazılması:
        hedef_ip = sistem.ip_adresi
        hedef_port = sistem.port
        protokol = sistem.baglanti_tipi
        deneme = sistem.maks_deneme
        timeout = sistem.zaman_asimi
        
        log_mesaji = f"Baglaniliyor: {hedef_ip}:{hedef_port} ({protokol}) - Deneme: {deneme}, Timeout: {timeout}"
        print(log_mesaji)
        
        # Kendi sınıfından hiçbir değişkene erişilmiyor!
        return log_mesaji

    def veri_temizleme_yardimcisi(self, metin):
        # Bu metot da sınıfa ait hiçbir üye değişkene (self.ana_veri vb.) erişmediği için
        # LCOM/Cohesion skorunu olumsuz etkiler.
        temizlenmis = metin.strip().replace("\n", " ").lower()
        return temizlenmis
