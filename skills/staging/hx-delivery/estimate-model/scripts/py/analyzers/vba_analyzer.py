"""
VBA Analyzer

Analyzes VBA macros using oletools (olevba) directly.
Falls back to ZIP inspection (presence only) if oletools is unavailable.
"""

import re
import sys
import zipfile


def _detect_external_integrations(all_code: str) -> dict:
    """Detect external integration patterns in VBA code."""
    integrations = []

    # --- ODBC / SQL integrations ---
    has_adodb = bool(re.search(r'\bADODB\b', all_code, re.IGNORECASE))
    has_dao   = bool(re.search(r'\bDAO\b', all_code, re.IGNORECASE))
    has_odbc_conn = bool(re.search(
        r'DSN=|ODBC;|Driver=\{|Provider=SQLOLEDB|Provider=MSOLEDBSQL|Provider=Microsoft\.ACE',
        all_code, re.IGNORECASE
    ))
    has_query_table = bool(re.search(r'QueryTable|\.CommandText\s*=', all_code, re.IGNORECASE))
    has_sql_read  = bool(re.search(r'\bSELECT\b.{0,80}\bFROM\b', all_code, re.IGNORECASE | re.DOTALL))
    has_sql_write = bool(re.search(r'\b(INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM)\b', all_code, re.IGNORECASE))

    if has_adodb or has_dao or has_odbc_conn or has_query_table:
        techs = []
        if has_adodb:       techs.append("ADODB")
        if has_dao:         techs.append("DAO")
        if has_odbc_conn:   techs.append("ODBC connection string")
        if has_query_table: techs.append("QueryTable")

        if has_sql_write:
            integrations.append({
                "type": "ODBC_PUSH",
                "label": "SQL/ODBC Write (Reporting Export)",
                "severity": "HIGH",
                "details": techs + ["SQL write operations detected (INSERT/UPDATE/DELETE)"],
                "complexityImpact": "HIGH",
                "note": "Writes data to external SQL database — likely feeds a reporting or BI pipeline. Migration must preserve this data flow.",
            })
        if has_sql_read:
            integrations.append({
                "type": "ODBC_PULL",
                "label": "SQL/ODBC Read (External Data Import)",
                "severity": "HIGH",
                "details": techs + ["SQL read operations detected (SELECT)"],
                "complexityImpact": "HIGH",
                "note": "Pulls data from customer-hosted SQL source — live data dependency. Target environment needs equivalent data access.",
            })
        if not has_sql_read and not has_sql_write:
            integrations.append({
                "type": "ODBC_UNKNOWN",
                "label": "Database Connectivity (Direction Unknown)",
                "severity": "MEDIUM",
                "details": techs,
                "complexityImpact": "MEDIUM",
                "note": "Database connection objects present but SQL direction unclear — manual VBA review required.",
            })

    # --- HTTP / API calls ---
    api_checks = [
        ("MSXML2/WinHTTP (HTTP requests)",         r'MSXML2\.XMLHTTP|WinHttp\.WinHttpRequest'),
        ("Bloomberg BLP API (COM automation)",     r'blpapi|Bloomberg\.Session|CreateObject\s*\(\s*["\']Bloomberg'),
        ("Refinitiv/Reuters Eikon API",            r'Refinitiv|Eikon\.|Reuters\.|RDP\.Session|TR\.Connect'),
        ("Generic HTTP verbs (GET/POST/etc.)",     r'\.Open\s+"(?:GET|POST|PUT|DELETE|PATCH)"'),
        ("PowerShell HTTP invocation",             r'Invoke-WebRequest|Invoke-RestMethod|WebClient\.DownloadString'),
    ]
    for label, pattern in api_checks:
        if re.search(pattern, all_code, re.IGNORECASE):
            integrations.append({
                "type": "API_CALL",
                "label": f"External API Call ({label})",
                "severity": "HIGH",
                "details": [label],
                "complexityImpact": "HIGH",
                "note": "Direct HTTP/API integration — requires network access, authentication, and endpoint availability in target environment.",
            })

    # --- Financial data package VBA references ---
    # Note: CapIQ/Bloomberg worksheet formula functions (=CIQ(), =BDP()) appear in
    # cell formulas rather than VBA and are not captured here — review formula analysis separately.
    pkg_checks = [
        ("Capital IQ (CapIQ) COM/VBA",      r'CiqGwf|CIQGWF|CIQGet|CIQ_API|CreateObject.*CIQ'),
        ("Bloomberg Excel Add-in VBA API",  r'BloombergData|BLP\.Get|CreateObject.*Bloomberg\.Data'),
        ("FactSet VBA API",                 r'FactSet\.|FDSConnect|CreateObject.*FactSet'),
        ("SNL Financial VBA",               r'SNLFinancial|CreateObject.*SNL\b|SNL_Connect'),
        ("Moody's Analytics VBA",           r"Moody.s\s*Analytics|CreditEdge|CreateObject.*Moody"),
    ]
    for label, pattern in pkg_checks:
        if re.search(pattern, all_code, re.IGNORECASE):
            integrations.append({
                "type": "DATA_PACKAGE",
                "label": f"Financial Data Package ({label})",
                "severity": "HIGH",
                "details": [label],
                "complexityImpact": "HIGH",
                "note": f"{label} VBA integration — requires licensed subscription and add-in installation in target environment.",
            })

    if not integrations:
        overall = "NONE"
    elif any(i["complexityImpact"] == "HIGH" for i in integrations):
        overall = "HIGH"
    elif any(i["complexityImpact"] == "MEDIUM" for i in integrations):
        overall = "MEDIUM"
    else:
        overall = "LOW"

    return {
        "detected": bool(integrations),
        "integrations": integrations,
        "totalCount": len(integrations),
        "overallComplexityImpact": overall,
    }


def _normalize_result(raw: dict) -> dict:
    """Add numeric complexity score to raw oletools result."""
    level = raw.get("complexity", {}).get("level", "NONE")
    score = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}.get(level, 0)
    patterns = raw.get("patterns", {})
    if patterns.get("externalDLLs"):  score += 1
    if patterns.get("databaseAccess"): score += 0.5
    if patterns.get("apiCalls"):       score += 0.5
    if raw.get("modules", {}).get("userForms", 0) > 3: score += 0.5
    if raw.get("modules", {}).get("class", 0) > 2:     score += 0.5

    # Boost score for external integrations (each HIGH integration adds 0.5)
    integrations = raw.get("externalIntegrations", {})
    for intg in integrations.get("integrations", []):
        if intg.get("complexityImpact") == "HIGH":
            score += 0.5
        elif intg.get("complexityImpact") == "MEDIUM":
            score += 0.25

    score = min(score, 5)

    result = dict(raw)
    if "complexity" in result:
        result["complexity"] = dict(result["complexity"])
        result["complexity"]["score"] = score
    result["accessible"] = True
    result["passwordProtected"] = False
    result["trustCenterBlocked"] = False
    return result


class VBAAnalyzer:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def _has_vba_binary(self) -> bool:
        try:
            with zipfile.ZipFile(self.file_path) as zf:
                return "xl/vbaProject.bin" in zf.namelist()
        except Exception:
            return False

    def analyze(self) -> dict:
        has_binary = self._has_vba_binary()

        if not has_binary:
            return {
                "hasVBA": False, "accessible": True, "passwordProtected": False,
                "trustCenterBlocked": False, "totalLines": 0, "totalProcedures": 0,
                "totalComponents": 0,
                "diagnostic": "No VBA project found in file (xl/vbaProject.bin does not exist)",
                "complexity": {"level": "NONE", "score": 0, "factors": []},
                "modules": {"standard": 0, "class": 0, "userForms": 0, "worksheet": 0, "total": 0},
                "patterns": {}, "procedures": [],
            }

        # Try oletools analysis
        try:
            from oletools.olevba import VBA_Parser
            result = self._analyze_with_oletools(VBA_Parser)
            if result:
                return _normalize_result(result)
        except ImportError:
            print("  (oletools not available - VBA presence detected but not analyzed)", file=sys.stderr)
        except Exception as e:
            print(f"  Warning: oletools VBA analysis failed - {e}", file=sys.stderr)

        # Fallback: VBA binary exists but can't be read
        password_hint = "password" in str(sys.exc_info()[1]).lower() if sys.exc_info()[1] else False
        return {
            "hasVBA": True, "accessible": False,
            "passwordProtected": password_hint,
            "trustCenterBlocked": False, "totalLines": 0, "totalProcedures": 0,
            "totalComponents": 0,
            "diagnostic": "VBA project detected (xl/vbaProject.bin exists) but cannot be read - likely password protected",
            "complexity": {"level": "UNKNOWN", "score": 0, "factors": ["VBA project is password protected"]},
            "modules": {"standard": 0, "class": 0, "userForms": 0, "worksheet": 0, "total": 0},
            "patterns": {}, "procedures": [],
        }

    def _analyze_with_oletools(self, VBA_Parser) -> dict:
        vba = VBA_Parser(self.file_path)
        try:
            if not vba.detect_vba_macros():
                return {
                    "hasVBA": False, "accessible": True, "passwordProtected": False,
                    "totalLines": 0, "totalProcedures": 0, "totalComponents": 0,
                    "modules": {"standard": 0, "class": 0, "userForms": 0, "worksheet": 0},
                    "diagnostic": "No VBA macros detected in file",
                    "complexity": {"level": "NONE", "factors": []},
                    "patterns": {}, "procedures": [],
                }

            modules = {"standard": [], "class": [], "userForms": [], "worksheet": [], "thisWorkbook": None}
            total_lines = 0
            procedures = []
            all_code = ""

            for (_filename, stream_path, vba_filename, vba_code) in vba.extract_macros():
                if not vba_code:
                    continue
                lines = len(vba_code.splitlines())
                total_lines += lines
                all_code += vba_code + "\n"
                info = {"Name": vba_filename, "Lines": lines}
                if "Modules/" in stream_path or vba_filename.startswith("Module"):
                    modules["standard"].append(info)
                elif vba_filename == "ThisWorkbook":
                    modules["thisWorkbook"] = info
                elif "Sheet" in vba_filename or stream_path.startswith("xl/"):
                    modules["worksheet"].append(info)
                elif vba_filename.startswith(("UserForm", "Form")):
                    modules["userForms"].append(info)
                elif vba_filename.startswith("Class"):
                    modules["class"].append(info)
                else:
                    modules["standard"].append(info)
                proc_pat = r'^\s*(?:Public|Private|Friend)?\s*(?:Sub|Function)\s+(\w+)'
                for line in vba_code.splitlines():
                    m = re.match(proc_pat, line, re.IGNORECASE)
                    if m:
                        procedures.append(f"{vba_filename}.{m.group(1)}")

            patterns = {
                "apiCalls": bool(re.search(r'CreateObject.*MSXML2\.XMLHTTP|CreateObject.*WinHttp\.WinHttpRequest', all_code, re.IGNORECASE)),
                "fileIO": bool(re.search(r'Open.*For.*As|FileSystemObject|CreateObject.*Scripting\.FileSystemObject', all_code, re.IGNORECASE)),
                "databaseAccess": bool(re.search(r'ADODB|DAO\.|CreateObject.*ADODB', all_code, re.IGNORECASE)),
                "externalDLLs": bool(re.search(r'Declare\s+(?:PtrSafe\s+)?(?:Function|Sub)', all_code, re.IGNORECASE)),
                "emailOutlook": bool(re.search(r'CreateObject.*Outlook\.Application', all_code, re.IGNORECASE)),
                "userForms": len(modules["userForms"]) > 0,
                "workbookEvents": modules["thisWorkbook"] is not None and modules["thisWorkbook"]["Lines"] > 0,
                "worksheetEvents": any(m["Lines"] > 0 for m in modules["worksheet"]),
                "errorHandling": bool(re.search(r'On Error', all_code, re.IGNORECASE)),
                "applicationEvents": bool(re.search(r'Application\.(OnTime|OnKey)', all_code, re.IGNORECASE)),
            }

            complexity = "LOW"
            factors = []
            if total_lines > 1000:
                complexity = "HIGH"; factors.append("Large codebase (1000+ lines)")
            elif total_lines > 500:
                complexity = "MEDIUM"; factors.append("Moderate codebase (500+ lines)")
            elif total_lines > 100:
                complexity = "MEDIUM"; factors.append("Non-trivial codebase (100+ lines)")
            if patterns["apiCalls"]:
                factors.append("External API integration")
                if complexity == "LOW": complexity = "MEDIUM"
            if patterns["databaseAccess"]:
                factors.append("Database connectivity")
                if complexity == "LOW": complexity = "MEDIUM"
            if patterns["externalDLLs"]:
                factors.append("Native DLL calls (Windows API)"); complexity = "HIGH"
            if modules["userForms"]:
                factors.append(f"Custom user forms ({len(modules['userForms'])} forms)")
            if modules["class"]:
                factors.append(f"Object-oriented design ({len(modules['class'])} classes)")

            ws_with_lines = [m for m in modules["worksheet"] if m["Lines"] > 0]
            total_comps = len(modules["standard"]) + len(modules["class"]) + len(modules["userForms"]) + len(modules["worksheet"])

            return {
                "hasVBA": True, "accessible": True, "passwordProtected": False,
                "totalLines": total_lines, "totalProcedures": len(procedures),
                "totalComponents": total_comps,
                "projectName": "VBAProject",
                "modules": {
                    "standard": len(modules["standard"]),
                    "class": len(modules["class"]),
                    "userForms": len(modules["userForms"]),
                    "worksheet": len(ws_with_lines),
                    "total": len(modules["standard"]) + len(modules["class"]) + len(modules["userForms"]),
                },
                "patterns": patterns,
                "complexity": {"level": complexity, "factors": factors},
                "procedures": procedures[:20],
                "moduleDetails": {
                    "standard": modules["standard"],
                    "class": modules["class"],
                    "userForms": modules["userForms"],
                    "worksheet": ws_with_lines[:10],
                },
                "externalIntegrations": _detect_external_integrations(all_code),
            }
        finally:
            vba.close()

    @staticmethod
    def is_macro_enabled(file_name: str) -> bool:
        return bool(re.search(r'\.(xlsm|xla|xlam)$', file_name, re.IGNORECASE))
