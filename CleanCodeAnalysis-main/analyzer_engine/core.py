# analyzer_engine/core.py
import ast
from radon.complexity import cc_visit
from radon.metrics import mi_visit, h_visit

class AdvancedAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.classes = []
        self.functions = []
        self.violations = []
        self.imported_names = set()
        self.used_names = set()

    def visit_Import(self, node):
        for name in node.names:
            alias = name.asname or name.name
            self.imported_names.add((alias, node.lineno, "Import"))
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for name in node.names:
            alias = name.asname or name.name
            self.imported_names.add((alias, node.lineno, "ImportFrom"))
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        # Calculate class LOC
        class_loc = node.end_lineno - node.lineno + 1
        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        
        # Calculate LCOM1 (Lack of Cohesion of Methods)
        lcom_score = self.calculate_lcom(methods)
        
        self.classes.append({
            "name": node.name,
            "line": node.lineno,
            "loc": class_loc,
            "methods_count": len(methods),
            "lcom": lcom_score
        })
        
        # DR-02: God Class Detection
        if class_loc >= 150 or len(methods) >= 8:
            if lcom_score >= 5:
                self.violations.append({
                    "type": "God Class İhlali",
                    "severity": "CRITICAL",
                    "line": node.lineno,
                    "description": f"'{node.name}' sınıfı God Class adayı. LOC: {class_loc}, Metot Sayısı: {len(methods)}, LCOM: {lcom_score}."
                })
                
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # Function LOC
        func_loc = node.end_lineno - node.lineno + 1
        self.functions.append({
            "name": node.name,
            "line": node.lineno,
            "loc": func_loc,
            "args_count": len(node.args.args)
        })

        # DR-05: Too Many Arguments
        # Exclude self/cls in method definitions
        args_limit = 4
        actual_args = [a.arg for a in node.args.args if a.arg not in ('self', 'cls')]
        if len(actual_args) > args_limit:
            self.violations.append({
                "type": "Too Many Arguments (Aşırı Parametre)",
                "severity": "MAJOR",
                "line": node.lineno,
                "description": f"'{node.name}' metodu çok fazla parametre alıyor ({len(actual_args)} > {args_limit})."
            })

        # Deep Nesting
        nesting_depth = self.get_nesting_depth(node)
        if nesting_depth > 3:
            self.violations.append({
                "type": "Deep Nesting (Aşırı Dallanma)",
                "severity": "MAJOR",
                "line": node.lineno,
                "description": f"'{node.name}' metodu aşırı iç içe geçmiş yapılara sahip (Derinlik: {nesting_depth} > 3)."
            })

        # Feature Envy (Basic static approximation)
        self.check_feature_envy(node)

        # Unused local variables
        self.check_unused_locals(node)

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def calculate_lcom(self, methods):
        if len(methods) <= 1:
            return 0
        
        # Find fields accessed by each method (self.field_name)
        method_fields = {}
        for m in methods:
            fields = set()
            for child in ast.walk(m):
                if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name) and child.value.id == 'self':
                    fields.add(child.attr)
            method_fields[m.name] = fields

        P = 0
        Q = 0
        method_names = list(method_fields.keys())
        n = len(method_names)
        
        for i in range(n):
            for j in range(i + 1, n):
                f1 = method_fields[method_names[i]]
                f2 = method_fields[method_names[j]]
                if len(f1.intersection(f2)) == 0:
                    P += 1
                else:
                    Q += 1
        
        return (P - Q) if P > Q else 0

    def get_nesting_depth(self, func_node):
        max_depth = [0]
        
        def walk(node, depth):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                depth += 1
                if depth > max_depth[0]:
                    max_depth[0] = depth
            for child in ast.iter_child_nodes(node):
                walk(child, depth)
                
        for child in func_node.body:
            walk(child, 0)
        return max_depth[0]

    def check_feature_envy(self, func_node):
        self_accesses = 0
        other_accesses = {}
        
        for child in ast.walk(func_node):
            if isinstance(child, ast.Attribute):
                if isinstance(child.value, ast.Name):
                    obj_name = child.value.id
                    if obj_name == 'self':
                        self_accesses += 1
                    elif obj_name not in ('cls', 'self'):
                        other_accesses[obj_name] = other_accesses.get(obj_name, 0) + 1
                        
        for obj, count in other_accesses.items():
            if count > 3 and count > self_accesses * 2:
                self.violations.append({
                    "type": "Feature Envy İhlali",
                    "severity": "MINOR",
                    "line": func_node.lineno,
                    "description": f"'{func_node.name}' metodu '{obj}' nesnesine aşırı bağımlı görünüyor ({count} dış erişim)."
                })

    def check_unused_locals(self, func_node):
        stored_names = {}
        loaded_names = set()
        
        # Exclude common convention names or double underscore names
        for child in ast.walk(func_node):
            if isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Store):
                    if child.id != 'self' and not child.id.startswith('_'):
                        stored_names[child.id] = child.lineno
                elif isinstance(child.ctx, ast.Load):
                    loaded_names.add(child.id)
                    
        for name, line in stored_names.items():
            if name not in loaded_names:
                # check if it's a parameter
                is_param = any(a.arg == name for a in func_node.args.args)
                if not is_param:
                    self.violations.append({
                        "type": "Gereksiz Değişken (Unused Local)",
                        "severity": "MINOR",
                        "line": line,
                        "description": f"'{name}' yerel değişkeni tanımlanmış fakat hiçbir yerde kullanılmıyor."
                    })


def kodu_analiz_et(kod_icerigi: str, dosya_adi: str = "PastedCode.py"):
    sonuclar = {
        "uzun_metotlar": [],
        "karmasiklik": [],
        "bakim_yapilabilirlik_puani": 100.0,
        "halstead": {},
        "lcom": [],
        "violations": [],
        "technical_debt": 0,
        "quality_grade": "A",
        "quality_gate": "PASSED"
    }

    if not kod_icerigi.strip():
        return sonuclar

    # 1. AST AYRIŞTIRMA VE GELİŞMİŞ ANALİZLER
    try:
        agac = ast.parse(kod_icerigi)
    except SyntaxError as e:
        sonuclar["violations"].append({
            "type": "Sözdizimi Hatası (Syntax Error)",
            "severity": "CRITICAL",
            "line": e.lineno or 1,
            "description": f"Sözdizimi hatası nedeniyle kod analiz edilemedi: {e.msg}"
        })
        sonuclar["violations"][0]["cost_mins"] = 120
        sonuclar["violations"][0]["file"] = dosya_adi
        sonuclar["technical_debt"] = 120
        sonuclar["quality_gate"] = "FAILED"
        sonuclar["quality_grade"] = "F"
        sonuclar["bakim_yapilabilirlik_puani"] = 0.0
        return sonuclar

    analyzer = AdvancedAnalyzer()
    analyzer.visit(agac)

    # 2. UZUN METOT VE LOC KONTROLÜ
    for func in analyzer.functions:
        if func["loc"] > 15:  # SDD threshold is low for education purposes, let's keep 15
            sonuclar["uzun_metotlar"].append({
                "fonksiyon": func["name"],
                "satir_sayisi": func["loc"],
                "uyari": "Long Method İhlali"
            })
            analyzer.violations.append({
                "type": "Long Method İhlali",
                "severity": "MAJOR",
                "line": func["line"],
                "description": f"'{func['name']}' metodu {func['loc']} satır uzunluğunda (Önerilen maksimum: 15)."
            })

    # 3. MCCABE DÖNGÜSEL KARMAŞIKLIĞI
    try:
        karmasiklik_sonuclari = cc_visit(kod_icerigi)
        for sonuc in karmasiklik_sonuclari:
            risk = "Güvenli"
            if sonuc.complexity > 20:
                risk = "Kabul Edilemez Risk"
            elif sonuc.complexity > 10:
                risk = "Yüksek Riskli"
                
            sonuclar["karmasiklik"].append({
                "metot": sonuc.name,
                "skor": sonuc.complexity,
                "risk": risk
            })

            if sonuc.complexity > 10:
                analyzer.violations.append({
                    "type": "McCabe Karmaşıklığı İhlali",
                    "severity": "MAJOR" if sonuc.complexity <= 20 else "CRITICAL",
                    "line": sonuc.lineno,
                    "description": f"'{sonuc.name}' metodu yüksek McCabe karmaşıklığına sahip (Skor: {sonuc.complexity} > 10)."
                })
    except Exception:
        pass

    # 4. BAKIM YAPILABİLİRLİK ENDEKSİ
    try:
        mi_skoru = mi_visit(kod_icerigi, multi=False)
        sonuclar["bakim_yapilabilirlik_puani"] = round(mi_skoru, 2)
    except Exception:
        sonuclar["bakim_yapilabilirlik_puani"] = 50.0

    # 5. HALSTEAD METRİKLERİ
    try:
        h_res = h_visit(kod_icerigi)
        sonuclar["halstead"] = {
            "vocabulary": h_res.total.vocabulary,
            "length": h_res.total.length,
            "volume": round(h_res.total.volume, 2),
            "difficulty": round(h_res.total.difficulty, 2),
            "effort": round(h_res.total.effort, 2),
            "time": round(h_res.total.time, 2),
            "bugs": round(h_res.total.bugs, 3)
        }
    except Exception:
        sonuclar["halstead"] = {
            "vocabulary": 0, "length": 0, "volume": 0.0, "difficulty": 0.0, "effort": 0.0, "time": 0.0, "bugs": 0.0
        }

    # 6. LCOM RAPORLANMASI
    sonuclar["lcom"] = analyzer.classes

    # 7. UNUSED IMPORTS KONTROLÜ
    for alias, line, imp_type in analyzer.imported_names:
        # Check if the imported name or its subparts is ever loaded in Name nodes
        # Handling package imports (e.g. if 'import os.path' and we call 'os.path.join', used name might contain 'os')
        base_name = alias.split('.')[0]
        if base_name not in analyzer.used_names:
            analyzer.violations.append({
                "type": f"Gereksiz Kütüphane ({imp_type})",
                "severity": "MINOR",
                "line": line,
                "description": f"'{alias}' kütüphanesi içe aktarılmış (import) fakat hiçbir yerde kullanılmıyor."
            })

    # 8. TEKNİK BORÇ HESAPLAMA (Dakika Cinsinden)
    debt_table = {
        "Sözdizimi Hatası (Syntax Error)": 120,
        "God Class İhlali": 60,
        "Long Method İhlali": 15,
        "McCabe Karmaşıklığı İhlali": 20,
        "Too Many Arguments (Aşırı Parametre)": 15,
        "Deep Nesting (Aşırı Dallanma)": 20,
        "Feature Envy İhlali": 20,
        "Gereksiz Değişken (Unused Local)": 5,
        "Gereksiz Kütüphane (Import)": 5,
        "Gereksiz Kütüphane (ImportFrom)": 5,
        "Kopya Kod (Duplicate Code)": 30
    }

    total_debt = 0
    formatted_violations = []
    for v in analyzer.violations:
        v_type = v["type"]
        cost = debt_table.get(v_type, 10)
        total_debt += cost
        formatted_violations.append({
            "type": v_type,
            "severity": v["severity"],
            "line": v["line"],
            "description": v["description"],
            "cost_mins": cost,
            "file": dosya_adi
        })

    # Sort violations by line number
    formatted_violations.sort(key=lambda x: x["line"])
    sonuclar["violations"] = formatted_violations
    sonuclar["technical_debt"] = total_debt

    # 9. KALİTE DERECESİ VE GEÇİŞ DURUMU
    mi = sonuclar["bakim_yapilabilirlik_puani"]
    if mi >= 85:
        sonuclar["quality_grade"] = "A"
    elif mi >= 70:
        sonuclar["quality_grade"] = "B"
    elif mi >= 55:
        sonuclar["quality_grade"] = "C"
    elif mi >= 40:
        sonuclar["quality_grade"] = "D"
    else:
        sonuclar["quality_grade"] = "F"

    # Quality Gate
    # Fails if grade is D or F, or if there is any CRITICAL violation
    has_critical = any(v["severity"] == "CRITICAL" for v in formatted_violations)
    if sonuclar["quality_grade"] in ("D", "F") or has_critical:
        sonuclar["quality_gate"] = "FAILED"
    else:
        sonuclar["quality_gate"] = "PASSED"

    return sonuclar


def projeyi_analiz_et(dosyalar: list):
    """
    dosyalar: list of dict, örn: [{"path": "main.py", "content": "print('hello')"}]
    """
    proje_raporu = {
        "dosya_sayisi": len(dosyalar),
        "toplam_satir": 0,
        "bakim_yapilabilirlik_ortalamasi": 0.0,
        "toplam_teknik_borc": 0,
        "quality_gate": "PASSED",
        "quality_grade": "A",
        "dosyalar": {},
        "violations": [],
        "halstead_toplam": {
            "volume": 0.0, "difficulty": 0.0, "effort": 0.0, "time": 0.0, "bugs": 0.0
        }
    }

    if not dosyalar:
        proje_raporu["quality_grade"] = "F"
        proje_raporu["quality_gate"] = "FAILED"
        return proje_raporu

    mi_list = []
    total_volume = 0.0
    total_effort = 0.0
    total_bugs = 0.0
    total_vocabulary = 0
    total_length = 0

    # 1. HER BİR DOSYAYI TEK TEK ANALİZ ET
    for dosya in dosyalar:
        path = dosya["path"]
        content = dosya["content"]
        
        # Calculate LOC
        lines = content.splitlines()
        proje_raporu["toplam_satir"] += len(lines)

        res = kodu_analiz_et(content, path)
        
        proje_raporu["dosyalar"][path] = res
        proje_raporu["violations"].extend(res["violations"])
        proje_raporu["toplam_teknik_borc"] += res["technical_debt"]
        
        mi_list.append(res["bakim_yapilabilirlik_puani"])
        
        # Aggregate Halstead
        h = res.get("halstead", {})
        total_vocabulary += h.get("vocabulary", 0)
        total_length += h.get("length", 0)
        total_volume += h.get("volume", 0.0)
        total_effort += h.get("effort", 0.0)
        total_bugs += h.get("bugs", 0.0)

    # 2. KOPYA KOD (DUPLICATE CODE) TESPİTİ
    # Simple line-based comparison for blocks of >= 6 lines
    duplications = detect_duplications(dosyalar)
    for dup in duplications:
        proje_raporu["toplam_teknik_borc"] += 30  # Add 30 mins for each duplication
        v = {
            "type": "Kopya Kod (Duplicate Code)",
            "severity": "MAJOR",
            "line": dup["line1"],
            "description": f"Bu kod bloğu ile '{dup['file2']}' (satır {dup['line2']}) arasında mükemmel eşleşme var ({dup['length']} satır).",
            "cost_mins": 30,
            "file": dup["file1"]
        }
        proje_raporu["violations"].append(v)
        # Also add to the file's individual violations
        if dup["file1"] in proje_raporu["dosyalar"]:
            proje_raporu["dosyalar"][dup["file1"]]["violations"].append(v)
            proje_raporu["dosyalar"][dup["file1"]]["technical_debt"] += 30

    # 3. PROJE GENEL METRİKLERİNİ HESAPLA
    if mi_list:
        proje_raporu["bakim_yapilabilirlik_ortalamasi"] = round(sum(mi_list) / len(mi_list), 2)
    else:
        proje_raporu["bakim_yapilabilirlik_ortalamasi"] = 100.0

    proje_raporu["halstead_toplam"] = {
        "vocabulary": total_vocabulary,
        "length": total_length,
        "volume": round(total_volume, 2),
        "effort": round(total_effort, 2),
        "difficulty": round(total_volume / 20.0 if total_volume > 0 else 0, 2), # simple approximation
        "bugs": round(total_bugs, 3),
        "time": round(total_effort / 18.0, 2)
    }

    # Project Quality Grade
    avg_mi = proje_raporu["bakim_yapilabilirlik_ortalamasi"]
    if avg_mi >= 85:
        proje_raporu["quality_grade"] = "A"
    elif avg_mi >= 70:
        proje_raporu["quality_grade"] = "B"
    elif avg_mi >= 55:
        proje_raporu["quality_grade"] = "C"
    elif avg_mi >= 40:
        proje_raporu["quality_grade"] = "D"
    else:
        proje_raporu["quality_grade"] = "F"

    # Quality Gate
    has_critical = any(v["severity"] == "CRITICAL" for v in proje_raporu["violations"])
    if proje_raporu["quality_grade"] in ("D", "F") or has_critical:
        proje_raporu["quality_gate"] = "FAILED"
    else:
        proje_raporu["quality_gate"] = "PASSED"

    # Sort all violations
    proje_raporu["violations"].sort(key=lambda x: (x["file"], x["line"]))

    return proje_raporu


def detect_duplications(dosyalar: list, min_length: int = 6):
    """
    Compares cleaned lines of files to find duplicate blocks of length >= min_length.
    """
    cleaned_files = {}
    for d in dosyalar:
        lines = d["content"].splitlines()
        cleaned_lines = []
        for i, l in enumerate(lines):
            cleaned = l.strip()
            # Skip empty lines and comments
            if cleaned and not cleaned.startswith('#'):
                cleaned_lines.append((i + 1, cleaned))
        cleaned_files[d["path"]] = cleaned_lines

    dups = []
    file_paths = list(cleaned_files.keys())
    n_files = len(file_paths)

    for i in range(n_files):
        f1 = file_paths[i]
        lines1 = cleaned_files[f1]
        
        for j in range(i, n_files):
            f2 = file_paths[j]
            lines2 = cleaned_files[f2]
            
            # If same file, avoid comparing overlapping regions, or just skip self-comparison for simplicity
            if f1 == f2:
                continue
                
            # Simple sliding window search
            len1 = len(lines1)
            len2 = len(lines2)
            
            idx1 = 0
            while idx1 <= len1 - min_length:
                best_match = None
                
                for idx2 in range(len2 - min_length + 1):
                    # Check match length starting from idx1 and idx2
                    match_len = 0
                    while (idx1 + match_len < len1 and 
                           idx2 + match_len < len2 and 
                           lines1[idx1 + match_len][1] == lines2[idx2 + match_len][1]):
                        match_len += 1
                        
                    if match_len >= min_length:
                        if not best_match or match_len > best_match["length"]:
                            best_match = {
                                "file1": f1,
                                "line1": lines1[idx1][0],
                                "file2": f2,
                                "line2": lines2[idx2][0],
                                "length": match_len
                            }
                
                if best_match:
                    dups.append(best_match)
                    idx1 += best_match["length"]
                else:
                    idx1 += 1
                    
    return dups
