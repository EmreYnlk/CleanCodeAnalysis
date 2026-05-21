#Clean Code Örneği
# Bu dosyadaki tüm yapılar temiz kod prensiplerine uygun olarak tasarlanmıştır.

import math

class DaireHesaplayici:
    """
    Bu sınıf yüksek uyum (High Cohesion) prensibine göre tasarlanmıştır. 
    Tüm metotlar sınıfın üye değişkeni olan 'self.yaricap' parametresini kullanır (LCOM: 0).
    """
    def __init__(self, yaricap: float):
        self.yaricap = yaricap

    def alan_hesapla(self) -> float:
        # Metot kısa ve tek sorumluluk (Single Responsibility) ilkesine uygundur.
        return math.pi * (self.yaricap ** 2)

    def cevre_hesapla(self) -> float:
        # Kod dallanma içermez, okunabilirliği yüksektir.
        return 2 * math.pi * self.yaricap
