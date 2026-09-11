import os
import posixpath
import hashlib
import json
import string
import random
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import database as db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ctf_secret_key_linux_web_2026")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 30  # 30 kun

# Initialize database
db.init_db()


# ── Auth decorator ───────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("username"):
            if request.is_json:
                return jsonify({"error": "login_required"}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated

# Quiz metadata (for status command and descriptions)
QUIZZES_CTF1 = {
    1: {
        "title": "quiz1: Kataloglar yaratish",
        "commands": "mkdir, cd, ls",
        "description": "~/quiz1 papkasi ichida 'images', 'docs', va 'documents' nomli 3 ta papka yarating.",
        "guide": "cat ~/quiz1/README.txt"
    },
    2: {
        "title": "quiz2: Yangi fayllar hosil qilish",
        "commands": "touch, ls",
        "description": "~/quiz2/docs papkasi ichida 'notes.txt' va 'todo.txt' fayllarini yarating.",
        "guide": "cat ~/quiz2/README.txt"
    },
    3: {
        "title": "quiz3: Faylga matn yozish va ko'rish",
        "commands": "nano, cat, echo",
        "description": "~/quiz3/notes.txt fayli ichiga 'linux200' so'zini yozing va saqlang.",
        "guide": "cat ~/quiz3/README.txt"
    },
    4: {
        "title": "quiz4: Jurnal faylidan kalitni qidirish",
        "commands": "head, tail, grep",
        "description": "~/quiz4/bigfile.log ichidagi 150-qatordagi KEY-... kalitini topib, ~/quiz4/answer.txt fayliga yozing.",
        "guide": "cat ~/quiz4/README.txt"
    },
    5: {
        "title": "quiz5: Katta hujjatlarni varaqlab o'qish",
        "commands": "less, more, grep",
        "description": "~/quiz5/bigfile2.txt ichidagi 900-qatordagi PASS-... kalitini topib, ~/quiz5/answer.txt ga yozing.",
        "guide": "cat ~/quiz5/README.txt"
    },
    6: {
        "title": "quiz6: Keraksiz fayllar va papkalarni o'chirish",
        "commands": "rm, rm -r",
        "description": "~/quiz6 papkasidagi 'temp1.txt', 'temp2.txt' va 'junk/' katalogini o'chiring. 'required.txt' tegishli emas!",
        "guide": "cat ~/quiz6/README.txt"
    },
    7: {
        "title": "quiz7: Ruxsatlarni o'zgartirish (Executable)",
        "commands": "chmod, ./script.sh",
        "description": "~/quiz7/script.sh fayliga ishga tushirish (chmod +x) ruxsatini bering va uni ishga tushiring.",
        "guide": "cat ~/quiz7/README.txt"
    },
    8: {
        "title": "quiz8: Fayl egaligini o'zgartirish (Ownership)",
        "commands": "sudo chown",
        "description": "~/quiz8/secret.txt faylining egaligini o'zingizga (chown) o'tkazing.",
        "guide": "cat ~/quiz8/README.txt"
    },
    9: {
        "title": "quiz9: Yashirin fayllarni izlash",
        "commands": "ls -la, cd, cat, find",
        "description": "~/quiz9 ichidagi qatlamli papkalarda yashiringan '.flag_part' faylini toping va uning tarkibini ~/quiz9/answer.txt ga yozing.",
        "guide": "cat ~/quiz9/README.txt"
    },
    10: {
        "title": "quiz10: CTF 1 Yakuniy buyruq va Flag olish",
        "commands": "chmod, ./final.sh, check",
        "description": "~/quiz10/final.sh skriptini bajariladigan qiling va ishga tushiring, so'ng terminalda 'check' deb yozing!",
        "guide": "cat ~/quiz10/README.txt"
    }
}

QUIZZES_CTF2 = {
    1: {
        "title": "quiz1: Yopiq katalogga kirish (Permissions)",
        "commands": "chmod, ls -la, cd, cat",
        "description": "~/quiz1 ichidagi 'secret_zone' katalogiga kirish ruxsatini to'g'rilang va ichidagi yashirin kalitni ~/quiz1/answer.txt ga yozing.",
        "guide": "cat ~/quiz1/README.txt"
    },
    2: {
        "title": "quiz2: O'qish huquqi cheklangan fayl",
        "commands": "chmod, cat",
        "description": "~/quiz2/confidential.txt fayliga o'qish huquqini bering va undagi kalitni ~/quiz2/answer.txt ga ko'chiring.",
        "guide": "cat ~/quiz2/README.txt"
    },
    3: {
        "title": "quiz3: Aniq so'zni qidirish va uning qator raqamini topish",
        "commands": "grep, cat",
        "description": "~/quiz3/mixed_words.txt ichidagi o'xshash so'zlar orasidan mustaqil 'BiGs0Z' so'zining qator raqamini toping va ~/quiz3/answer.txt ga yozing.",
        "guide": "cat ~/quiz3/README.txt"
    },
    4: {
        "title": "quiz4: Shovqin va registr tahlili",
        "commands": "grep, cat",
        "description": "~/quiz4/server_log.txt dagi DEBUG shovqinlarni filtrlab, auth_token kodini ~/quiz4/answer.txt ga yozing.",
        "guide": "cat ~/quiz4/README.txt"
    },
    5: {
        "title": "quiz5: Fayl hajmi bo'yicha qidiruv (Find by size)",
        "commands": "find, cat",
        "description": "~/quiz5/storage papkasidan aynan 1024 bayt hajmli faylni toping va undagi kalitni ~/quiz5/answer.txt ga yozing.",
        "guide": "cat ~/quiz5/README.txt"
    },
    6: {
        "title": "quiz6: Huquqi bo'yicha qidiruv (Find by permission)",
        "commands": "find, cat",
        "description": "~/quiz6/restricted ichidan 777 (xavfli ochiq) ruxsatli faylni aniqlang va undagi kalitni ~/quiz6/answer.txt ga yozing.",
        "guide": "cat ~/quiz6/README.txt"
    },
    7: {
        "title": "quiz7: Turi bo'yicha ajratish (Find by type)",
        "commands": "find, cat",
        "description": "~/quiz7/archive ichidan katalog emas, aynan oddiy fayl (file) turini toping va undagi kalitni ~/quiz7/answer.txt ga yozing.",
        "guide": "cat ~/quiz7/README.txt"
    },
    8: {
        "title": "quiz8: Qator tahlili (grep va wc)",
        "commands": "grep, wc, cat",
        "description": "~/quiz8/lines.txt ichidan TARGET_SECRET qator raqami hamda faylning umumiy qatorlar sonini aniqlang (format: QATOR|JAMI).",
        "guide": "cat ~/quiz8/README.txt"
    },
    9: {
        "title": "quiz9: Bo'sh fayllarni tozalash (Cleanup)",
        "commands": "find, rm, cat",
        "description": "~/quiz9/cleanup ichidagi bo'sh (empty) fayllar orasidan haqiqiy ma'lumotli faylni topib, kalitini ~/quiz9/answer.txt ga yozing.",
        "guide": "cat ~/quiz9/README.txt"
    },
    10: {
        "title": "quiz10: CTF 2 Yakuniy Sinov (Final Lockbox)",
        "commands": "chmod, find, grep, check",
        "description": "~/quiz10/lockbox katalogiga ruxsat bering, 512 baytli faylni toping, ichidagi FINAL_FLAG ni answer.txt ga yozing va 'check' bering!",
        "guide": "cat ~/quiz10/README.txt"
    }
}
QUIZZES = QUIZZES_CTF1

# Dynamic Step-by-Step Hints (4-urinish, 5-urinish, 6-urinish)
HINTS_CTF1 = {
    1: {
        "hint1": "💡 Maslahat (1-daraja): Papka yaratish buyrug'idan foydalaning (mkdir).",
        "hint2": "💡 Maslahat (2-daraja): 'mkdir images docs documents' deb bir nechta papkani bir vaqtda yaratish mumkin.",
        "hint3": "🚨 So'nggi maslahat: 'cd ~/quiz1 && mkdir images docs documents' buyrug'ini bering va 'check' deb tekshiring!"
    },
    2: {
        "hint1": "💡 Maslahat (1-daraja): Bo'sh fayl yaratish uchun 'touch' buyrug'i kerak.",
        "hint2": "💡 Maslahat (2-daraja): Avval 'cd docs' qiling, keyin 'touch notes.txt todo.txt' bering.",
        "hint3": "🚨 So'nggi maslahat: 'cd ~/quiz2/docs && touch notes.txt todo.txt' qiling va 'check' bering!"
    },
    3: {
        "hint1": "💡 Maslahat (1-daraja): Faylga matn yozish uchun 'echo' yoki 'nano' muharriridan foydalaning.",
        "hint2": "💡 Maslahat (2-daraja): 'echo \"linux200\" > notes.txt' buyrug'i matnni faylga to'g'ridan-to'g'ri yozadi.",
        "hint3": "🚨 So'nggi maslahat: 'echo \"linux200\" > ~/quiz3/notes.txt' buyrug'ini bering va 'check' deb tekshiring!"
    },
    4: {
        "hint1": "💡 Maslahat (1-daraja): Katta fayllardan ma'lumot izlash uchun 'grep' buyrug'idan foydalaning.",
        "hint2": "💡 Maslahat (2-daraja): 'grep KEY ~/quiz4/bigfile.log' buyrug'i kalit so'zni ekranga chiqaradi.",
        "hint3": "🚨 So'nggi maslahat: 'grep KEY ~/quiz4/bigfile.log' orqali chiqqan KEY-... ni nusxalab ~/quiz4/answer.txt ga yozing!"
    },
    5: {
        "hint1": "💡 Maslahat (1-daraja): Fayldan 'PASS-' so'zini 'grep' orqali qidiring.",
        "hint2": "💡 Maslahat (2-daraja): 'grep PASS ~/quiz5/bigfile2.txt' buyrug'ini bajaring.",
        "hint3": "🚨 So'nggi maslahat: 'grep PASS ~/quiz5/bigfile2.txt' natijasidagi PASS-... kodini ~/quiz5/answer.txt ga yozing!"
    },
    6: {
        "hint1": "💡 Maslahat (1-daraja): Fayl o'chirish uchun 'rm', papka o'chirish uchun 'rm -r' kerak.",
        "hint2": "💡 Maslahat (2-daraja): 'rm temp1.txt temp2.txt' va 'rm -r junk' qiling. 'required.txt' ga tegmang!",
        "hint3": "🚨 So'nggi maslahat: 'cd ~/quiz6 && rm temp1.txt temp2.txt && rm -r junk' qiling va 'check' bering!"
    },
    7: {
        "hint1": "💡 Maslahat (1-daraja): Skriptga bajarish (execute) huquqini berish kerak.",
        "hint2": "💡 Maslahat (2-daraja): 'chmod +x script.sh' qiling va './script.sh' orqali ishga tushiring.",
        "hint3": "🚨 So'nggi maslahat: 'cd ~/quiz7 && chmod +x script.sh && ./script.sh' bering, so'ng 'check' qiling!"
    },
    8: {
        "hint1": "💡 Maslahat (1-daraja): Fayl egasini o'zgartirish uchun 'chown' va 'sudo' buyruqlari kerak.",
        "hint2": "💡 Maslahat (2-daraja): 'sudo chown $(whoami) secret.txt' yoki 'sudo chown <username> secret.txt' ni bajaring.",
        "hint3": "🚨 So'nggi maslahat: 'cd ~/quiz8 && sudo chown $(whoami) secret.txt' qiling va 'check' bering!"
    },
    9: {
        "hint1": "💡 Maslahat (1-daraja): Nuqta bilan boshlanuvchi fayllar yashirin bo'ladi. 'ls -la' bilan ko'ring.",
        "hint2": "💡 Maslahat (2-daraja): 'cd level1/level2' ichiga kiring va 'ls -la' qilib '.flag_part' ni 'cat' qiling.",
        "hint3": "🚨 So'nggi maslahat: 'cat ~/quiz9/level1/level2/.flag_part > ~/quiz9/answer.txt' qiling va 'check' bering!"
    },
    10: {
        "hint1": "💡 Maslahat (1-daraja): Final skriptiga ijro huquqini bering va ishga tushiring.",
        "hint2": "💡 Maslahat (2-daraja): 'chmod +x final.sh' va './final.sh' qiling.",
        "hint3": "🚨 So'nggi maslahat: 'cd ~/quiz10 && chmod +x final.sh && ./final.sh' qiling va 'check' bering!"
    }
}

HINTS_CTF2 = {
    1: {
        "hint1": "💡 Maslahat (1-daraja): Papkaga kirish uchun unga 'execute' (x) huquqi zarur. 'chmod' yordamida ruxsatni to'g'rilang.",
        "hint2": "💡 Maslahat (2-daraja): 'chmod +rx secret_zone' yoki 'chmod 755 secret_zone' buyrug'ini bering, so'ng ichiga kiring.",
        "hint3": "🚨 So'nggi maslahat: 'chmod 755 ~/quiz1/secret_zone && cat ~/quiz1/secret_zone/.secret_flag > ~/quiz1/answer.txt' buyrug'ini bering!"
    },
    2: {
        "hint1": "💡 Maslahat (1-daraja): 'confidential.txt' faylida o'qish huquqi (r) yo'q. 'ls -l' bilan tekshiring va 'chmod' bilan o'qish huquqini bering.",
        "hint2": "💡 Maslahat (2-daraja): 'chmod +r confidential.txt' yoki 'chmod 644 confidential.txt' buyrug'idan foydalaning.",
        "hint3": "🚨 So'nggi maslahat: 'chmod +r ~/quiz2/confidential.txt && cat ~/quiz2/confidential.txt > ~/quiz2/answer.txt' qiling va 'check' bering!"
    },
    3: {
        "hint1": "💡 Maslahat (1-daraja): Fayl ichidagi yuzlab soxta so'zlar orasidan aynan mustaqil 'BiGs0Z' so'zini ajratib olish va uning qator raqamini ko'rsatish talab qilinadi.",
        "hint2": "💡 Maslahat (2-daraja): Qidiruv vositasining so'z chegarasi (-w) hamda qator raqamini ko'rsatish (-n) parametrlarini birgalikda ishlatib ko'ring.",
        "hint3": "🚨 So'nggi maslahat: 'grep -wn BiGs0Z ~/quiz3/mixed_words.txt' orqali chiqqan qator raqamini (23) ~/quiz3/answer.txt ga yozing!"
    },
    4: {
        "hint1": "💡 Maslahat (1-daraja): Shovqinli qatorlarni filtrlab tashlash (invert-match) yoki katta-kichik harflarni e'tiborsiz qoldirish kerak.",
        "hint2": "💡 Maslahat (2-daraja): 'grep -i auth_token' (registrga qaramay) yoki 'grep -v DEBUG' (DEBUG ni chiqarib tashlash) parametrlarini sinang.",
        "hint3": "🚨 So'nggi maslahat: 'grep -i auth_token ~/quiz4/server_log.txt' ni bajaring va tokenni ~/quiz4/answer.txt ga saqlang!"
    },
    5: {
        "hint1": "💡 Maslahat (1-daraja): Fayllarni birma-bir ochmang! 'find' buyrug'ining hajmni (size) filtrlash parametrini qo'llang.",
        "hint2": "💡 Maslahat (2-daraja): 'find' da baytlar bo'yicha qidirish parametri: '-size 1024c'.",
        "hint3": "🚨 So'nggi maslahat: 'find ~/quiz5/storage -size 1024c' orqali chiqqan faylni 'cat' qiling va kalitni ~/quiz5/answer.txt ga yozing!"
    },
    6: {
        "hint1": "💡 Maslahat (1-daraja): Ruxsatlar bo'yicha qidiruv uchun 'find' buyrug'ining '-perm' parametrini ishlating.",
        "hint2": "💡 Maslahat (2-daraja): 'find ~/quiz6/restricted -perm 777' buyrug'i aynan to'liq ochiq faylni topadi.",
        "hint3": "🚨 So'nggi maslahat: 'find ~/quiz6/restricted -perm 777' faylini aniqlang, tarkibini ko'rib ~/quiz6/answer.txt ga yozing!"
    },
    7: {
        "hint1": "💡 Maslahat (1-daraja): 'find' orqali faqat oddiy fayllarni (kataloglarni emas) qidirish mumkin.",
        "hint2": "💡 Maslahat (2-daraja): Faqat fayllarni topish parametri: '-type f'. 'find archive -type f' ni bering.",
        "hint3": "🚨 So'nggi maslahat: 'find ~/quiz7/archive -type f' orqali chiqqan fayl tarkibini ~/quiz7/answer.txt ga ko'chiring!"
    },
    8: {
        "hint1": "💡 Maslahat (1-daraja): So'z turgan qator raqamini 'grep -n' orqali, faylning umumiy qatorlar sonini esa 'wc -l' orqali aniqlang.",
        "hint2": "💡 Maslahat (2-daraja): 'grep -n TARGET_SECRET lines.txt' va 'wc -l lines.txt' buyruqlaridan chiqqan raqamlarni '|' bilan birlashtiring.",
        "hint3": "🚨 So'nggi maslahat: Nishon qatori 345, umumiy qatorlar 500. answer.txt ga '345|500' deb yozing!"
    },
    9: {
        "hint1": "💡 Maslahat (1-daraja): Bo'sh bo'lmagan (hajmi 0 dan katta) faylni topish uchun 'find' dan foydalaning.",
        "hint2": "💡 Maslahat (2-daraja): 'find ~/quiz9/cleanup -size +0c' parametri bo'sh bo'lmagan yagona haqiqiy faylni ko'rsatadi.",
        "hint3": "🚨 So'nggi maslahat: 'find ~/quiz9/cleanup -size +0c' faylini 'cat' qilib, ichidagi kalitni ~/quiz9/answer.txt ga yozing!"
    },
    10: {
        "hint1": "💡 Maslahat (1-daraja): Avval 'lockbox' papkasiga 'chmod 755' bering, so'ng 'find -size 512c' orqali faylni toping.",
        "hint2": "💡 Maslahat (2-daraja): Topilgan fayl ichidan 'grep -w FINAL_FLAG' orqali yakuniy kalitni ajratib oling.",
        "hint3": "🚨 So'nggi maslahat: 'chmod 755 ~/quiz10/lockbox', 'find ~/quiz10/lockbox -size 512c' faylidagi kodni ~/quiz10/answer.txt ga yozing va 'check' bering!"
    }
}
HINTS = HINTS_CTF1


def generate_key(prefix, length=8):
    chars = string.ascii_uppercase + string.digits
    return prefix + ''.join(random.choices(chars, k=length))


def get_user_fs(username):
    db.seed_student(username)
    ctf_status = db.get_student_ctf_status(username)
    active_ctf = ctf_status["active_ctf"]
    stage = ctf_status["ctf2_stage"] if active_ctf == 2 else ctf_status["ctf1_stage"]
    answers = db.get_student_answers(username)

    fs = {
        "/": {"type": "dir", "owner": "root", "mode": "755", "children": ["home", "var", "bin", "tmp", "etc"]},
        "/home": {"type": "dir", "owner": "root", "mode": "755", "children": [username]},
        f"/home/{username}": {
            "type": "dir", "owner": username, "mode": "700",
            "children": ["ROADMAP.txt"] + [f"quiz{i}" for i in range(1, min(stage + 1, 11))]
        }
    }

    if active_ctf == 1:
        _populate_ctf1_fs(fs, username, stage, answers)
    else:
        _populate_ctf2_fs(fs, username, stage, answers)

    return fs


def _populate_ctf1_fs(fs, username, stage, answers):
    fs[f"/home/{username}/ROADMAP.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================================================\n"
                "🚩 CTF 1: LINUX ASOSLARI ROADMAP (YO'L XARITASI) 🚩\n"
                "========================================================================\n\n"
                "📌 ASOSIY BUYRUQLAR:\n"
                "  • check   - Joriy bosqichdagi vazifangiz to'g'ri bajarilganini tekshiradi.\n"
                "  • status  - Hozir qaysi bosqichda ekanligingiz va vazifa shartini ko'rsatadi.\n\n"
                "🗺 CTF 1 BOSQICHLARI (1-10):\n"
                "   1. quiz1  | mkdir, cd, ls       | images, docs, documents papkalarini yaratish\n"
                "   2. quiz2  | touch, cd           | docs/ ichida notes.txt va todo.txt yaratish\n"
                "   3. quiz3  | nano, cat, echo     | notes.txt ichiga \"linux200\" yozish\n"
                "   4. quiz4  | head, tail, grep    | bigfile.log dan KEY-... ni topib answer.txt ga yozish\n"
                "   5. quiz5  | less, more, grep    | bigfile2.txt dan PASS-... ni topib answer.txt ga yozish\n"
                "   6. quiz6  | rm, rm -r           | Keraksiz fayl va papkalarni xavfsiz o'chirish\n"
                "   7. quiz7  | chmod, ./           | script.sh ga execute ruxsati berish va ishga tushirish\n"
                "   8. quiz8  | chown, sudo         | secret.txt faylini o'zingizga biriktirish\n"
                "   9. quiz9  | ls -la, cd, cat     | Yashirin .flag_part faylini topish va saqlash\n"
                "  10. quiz10 | CTF 1 Final         | final.sh ni ishga tushirish va 1-FLAG ni olish!\n\n"
                "💡 Eslatma: CTF 1 ning 10 ta bosqichini to'liq yakunlaganingizdan so'ng,\n"
                "   CTF 2 (Ilg'or Kiberxavfsizlik) avtomatik ochiladi!\n\n"
                "🚀 Boshlash uchun:\n"
                "  cd ~/quiz1\n"
                "  cat README.txt\n\n"
                "Omad tilaymiz!\n"
                "========================================================================"
            )
        }

    # ── quiz1: mkdir/cd/ls ──
    fs[f"/home/{username}/quiz1"] = {
        "type": "dir", "owner": username, "mode": "755", "children": ["README.txt"]
    }
    fs[f"/home/{username}/quiz1/README.txt"] = {
        "type": "file", "owner": username, "mode": "644",
        "content": (
            "========================================\n"
            "📌 QUIZ 1: Papkalar yaratish va navigatsiya\n"
            "========================================\n"
            "🎯 Mavzu: mkdir, cd, ls\n\n"
            "📝 Vazifa:\n"
            "  Ushbu 'quiz1' papkasi ichida 3 ta yangi papka yarating:\n"
            "  1) images\n"
            "  2) docs\n"
            "  3) documents\n\n"
            "💡 Foydalanishingiz mumkin bo'lgan buyruqlar:\n"
            "  Bu yerda 'mkdir', 'cd', 'ls' buyruqlaridan foydalanishingiz mumkin.\n\n"
            "✅ Tekshirish:\n"
            "  Bajarib bo'lgach, terminalda tekshiring:\n"
            "  check\n"
            "========================================"
        )
    }

    # ── quiz2: touch ──
    if stage >= 2:
        fs[f"/home/{username}/quiz2"] = {
            "type": "dir", "owner": username, "mode": "755", "children": ["README.txt", "docs"]
        }
        fs[f"/home/{username}/quiz2/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 2: Fayllar yaratish\n"
                "========================================\n"
                "🎯 Mavzu: touch, cd\n\n"
                "📝 Vazifa:\n"
                "  'docs' papkasi ichiga kiring va uning ichida 2 ta bo'sh fayl yarating:\n"
                "  1) notes.txt\n"
                "  2) todo.txt\n\n"
                "💡 Foydalanishingiz mumkin bo'lgan buyruqlar:\n"
                "  Bu yerda 'cd', 'touch', 'ls' buyruqlaridan foydalanishingiz mumkin.\n\n"
                "✅ Tekshirish:\n"
                "  Bajarib bo'lgach, terminalda tekshiring:\n"
                "  check\n"
                "========================================"
            )
        }
        fs[f"/home/{username}/quiz2/docs"] = {
            "type": "dir", "owner": username, "mode": "755", "children": []
        }

    # ── quiz3: nano/cat/echo ──
    if stage >= 3:
        fs[f"/home/{username}/quiz3"] = {
            "type": "dir", "owner": username, "mode": "755", "children": ["README.txt"]
        }
        fs[f"/home/{username}/quiz3/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 3: Faylga matn yozish va tahrirlash\n"
                "========================================\n"
                "🎯 Mavzu: nano, cat, echo\n\n"
                "📝 Vazifa:\n"
                "  Ushbu 'quiz3' papkasi ichida 'notes.txt' nomli fayl yarating (yoki tahrirlang)\n"
                "  va uning ichiga aynan quyidagi so'zni yozing:\n"
                "  linux200\n\n"
                "💡 Foydalanishingiz mumkin bo'lgan buyruqlar:\n"
                "  Fayl yaratish, tahrirlash va matnni ko'rish uchun 'nano', 'cat', 'echo'\n"
                "  buyruqlaridan foydalanishingiz mumkin.\n\n"
                "✅ Tekshirish:\n"
                "  Bajarib bo'lgach, terminalda tekshiring:\n"
                "  check\n"
                "========================================"
            )
        }

    # ── quiz4: head/tail/grep — kalit 150-qatorda ──
    if stage >= 4:
        key4 = answers.get(4, "KEY-DEFAULT1")
        log_lines = []
        for i in range(1, 150):
            log_lines.append(f"log satri {i} - hech narsa emas")
        log_lines.append(f"log satri 150 - MUHIM SO'Z: {key4}")
        for i in range(151, 301):
            log_lines.append(f"log satri {i} - hech narsa emas")

        fs[f"/home/{username}/quiz4"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["README.txt", "bigfile.log"]
        }
        fs[f"/home/{username}/quiz4/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 4: Katta log fayllaridan ma'lumot qidirish\n"
                "========================================\n"
                "🎯 Mavzu: head, tail, grep\n\n"
                "📝 Vazifa:\n"
                "  'bigfile.log' fayli ichida 150-qatorda maxsus kalit so'z (KEY-...) yashiringan.\n"
                "  Ushbu kalit so'zni toping va uni faqat o'zini 'answer.txt' nomli faylga yozing.\n"
                "  (Masalan: answer.txt ichida faqat KEY-ABC12345 bo'lishi kerak).\n\n"
                "💡 Foydalanishingiz mumkin bo'lgan buyruqlar:\n"
                "  Katta fayllardan aniq qator yoki matn qidirish uchun 'head', 'tail', 'grep', 'cat'\n"
                "  buyruqlaridan va '>' yo'naltirish belgisidan foydalanishingiz mumkin.\n\n"
                "✅ Tekshirish:\n"
                "  Bajarib bo'lgach, terminalda tekshiring:\n"
                "  check\n"
                "========================================"
            )
        }
        fs[f"/home/{username}/quiz4/bigfile.log"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": "\n".join(log_lines)
        }

    # ── quiz5: less/more/grep — kalit 900-qatorda ──
    if stage >= 5:
        key5 = answers.get(5, "PASS-DEFAULT1")
        big_lines = []
        for i in range(1, 900):
            big_lines.append(f"matn qatori {i}")
        big_lines.append(f"matn qatori 900 - kerakli kalit: {key5}")
        for i in range(901, 1001):
            big_lines.append(f"matn qatori {i}")

        fs[f"/home/{username}/quiz5"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["README.txt", "bigfile2.txt"]
        }
        fs[f"/home/{username}/quiz5/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 5: Sahifalab o'qish va qidiruv\n"
                "========================================\n"
                "🎯 Mavzu: less, more, grep\n\n"
                "📝 Vazifa:\n"
                "  'bigfile2.txt' matn fayli ichidan kerakli parolni (PASS-...) toping\n"
                "  va uni 'answer.txt' nomli faylga yozing.\n\n"
                "💡 Foydalanishingiz mumkin bo'lgan buyruqlar:\n"
                "  Faylni sahifalab ko'rish yoki qidirish uchun 'less', 'more', 'grep'\n"
                "  buyruqlaridan foydalanishingiz mumkin.\n\n"
                "✅ Tekshirish:\n"
                "  Bajarib bo'lgach, terminalda tekshiring:\n"
                "  check\n"
                "========================================"
            )
        }
        fs[f"/home/{username}/quiz5/bigfile2.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": "\n".join(big_lines)
        }

    # ── quiz6: rm/rm-r ──
    if stage >= 6:
        fs[f"/home/{username}/quiz6"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["README.txt", "temp1.txt", "temp2.txt", "junk", "required.txt"]
        }
        fs[f"/home/{username}/quiz6/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 6: Fayl va papkalarni o'chirish\n"
                "========================================\n"
                "🎯 Mavzu: rm, rm -r\n\n"
                "📝 Vazifa:\n"
                "  Ushbu papka ichidagi keraksiz elementlarni o'chiring:\n"
                "  1) 'temp1.txt' faylini o'chiring\n"
                "  2) 'temp2.txt' faylini o'chiring\n"
                "  3) 'junk' papkasini (va uning ichidagilarini) o'chiring\n"
                "  ⚠️ DIQQAT: 'required.txt' faylini O'CHIRMANG!\n\n"
                "💡 Foydalanishingiz mumkin bo'lgan buyruqlar:\n"
                "  Fayl va papkalarni o'chirish uchun 'rm' (va uning kerakli kalitlari),\n"
                "  holatni ko'rish uchun 'ls' buyrug'idan foydalanishingiz mumkin.\n\n"
                "✅ Tekshirish:\n"
                "  Bajarib bo'lgach, terminalda tekshiring:\n"
                "  check\n"
                "========================================"
            )
        }
        fs[f"/home/{username}/quiz6/temp1.txt"] = {
            "type": "file", "owner": username, "mode": "644", "content": "temporary data 1"
        }
        fs[f"/home/{username}/quiz6/temp2.txt"] = {
            "type": "file", "owner": username, "mode": "644", "content": "temporary data 2"
        }
        fs[f"/home/{username}/quiz6/required.txt"] = {
            "type": "file", "owner": username, "mode": "644", "content": "bu faylni o'chirmang"
        }
        fs[f"/home/{username}/quiz6/junk"] = {
            "type": "dir", "owner": username, "mode": "755", "children": ["old.log"]
        }
        fs[f"/home/{username}/quiz6/junk/old.log"] = {
            "type": "file", "owner": username, "mode": "644", "content": "old garbage log"
        }

    # ── quiz7: chmod ──
    if stage >= 7:
        fs[f"/home/{username}/quiz7"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["README.txt", "script.sh"]
        }
        fs[f"/home/{username}/quiz7/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 7: Fayl ruxsatlari (Permissions)\n"
                "========================================\n"
                "🎯 Mavzu: chmod, ./\n\n"
                "📝 Vazifa:\n"
                "  Ushbu papkada 'script.sh' skripti bor, lekin hozirda uni ishga tushirib bo'lmaydi\n"
                "  (ishga tushirish - execute huquqi yo'q).\n"
                "  1) Unga ishga tushirish huquqini bering\n"
                "  2) Skriptni ishga tushiring\n\n"
                "💡 Foydalanishingiz mumkin bo'lgan buyruqlar:\n"
                "  Fayl ruxsatlarini tekshirish va o'zgartirish uchun 'ls -l', 'chmod' buyruqlaridan\n"
                "  hamda './' orqali ishga tushirishdan foydalanishingiz mumkin.\n\n"
                "✅ Tekshirish:\n"
                "  Bajarib bo'lgach, terminalda tekshiring:\n"
                "  check\n"
                "========================================"
            )
        }
        fs[f"/home/{username}/quiz7/script.sh"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "#!/bin/bash\n"
                "DIR=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd)\"\n"
                "echo \"muvaffaqiyatli\" > \"$DIR/done.txt\"\n"
                "echo \"Skript ishga tushdi!\""
            )
        }

    # ── quiz8: chown ──
    if stage >= 8:
        fs[f"/home/{username}/quiz8"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["README.txt", "secret.txt"]
        }
        fs[f"/home/{username}/quiz8/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 8: Fayl egasini o'zgartirish (Ownership)\n"
                "========================================\n"
                "🎯 Mavzu: chown, sudo\n\n"
                "📝 Vazifa:\n"
                "  'secret.txt' fayli hozirda 'root' foydalanuvchisiga tegishli.\n"
                "  Fayl egasini (owner) o'z login nomingizga o'tkazing.\n\n"
                "💡 Foydali buyruqlar va misollar:\n"
                "  1) Hozirgi egasini ko'rish:\n"
                "     ls -l secret.txt\n\n"
                "  2) Egasini o'zingizga o'zgartirish:\n"
                f"     sudo chown {username} secret.txt\n"
                "     yoki:\n"
                "     sudo chown $(whoami) secret.txt\n\n"
                "✅ Tekshirish:\n"
                "  Bajarib bo'lgach, terminalda tekshiring:\n"
                "  check\n"
                "========================================"
            )
        }
        fs[f"/home/{username}/quiz8/secret.txt"] = {
            "type": "file", "owner": "root", "mode": "644",
            "content": "bu fayl hozircha root ga tegishli"
        }

    # ── quiz9: ls -la, cd, cat — qatlamli papka ──
    if stage >= 9:
        key9 = answers.get(9, "PART-DEFAULT1")
        fs[f"/home/{username}/quiz9"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["README.txt", "level1"]
        }
        fs[f"/home/{username}/quiz9/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 9: Yashirin fayllar va navigatsiya\n"
                "========================================\n"
                "🎯 Mavzu: ls -la, cd, cat\n\n"
                "📝 Vazifa:\n"
                "  Ushbu papka ichida qatlamli ichki papkalar mavjud.\n"
                "  Ularning ichida nuqta bilan boshlanadigan yashirin fayl (.flag_part) yashirilgan.\n"
                "  1) Yashirin fayllarni toping (ls -la bilan)\n"
                "  2) .flag_part ichidagi kodni topib, uni 'answer.txt' fayliga yozing.\n\n"
                "💡 Foydalanishingiz mumkin bo'lgan buyruqlar:\n"
                "  Yashirin fayllarni ko'rish va papkalar bo'ylab harakatlanish uchun\n"
                "  'ls' (yashirin fayllar kaliti bilan), 'cd', 'cat', 'find' buyruqlaridan foydalanishingiz mumkin.\n\n"
                "✅ Tekshirish:\n"
                "  Bajarib bo'lgach, terminalda tekshiring:\n"
                "  check\n"
                "========================================"
            )
        }
        fs[f"/home/{username}/quiz9/level1"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": [".hidden_hint", "level2"]
        }
        fs[f"/home/{username}/quiz9/level1/.hidden_hint"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": "davom eting... level2 papkasini ko'ring"
        }
        fs[f"/home/{username}/quiz9/level1/level2"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": [".flag_part"]
        }
        fs[f"/home/{username}/quiz9/level1/level2/.flag_part"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": key9
        }

    # ── quiz10: final ──
    if stage >= 10:
        fs[f"/home/{username}/quiz10"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["README.txt", "final.sh"]
        }
        fs[f"/home/{username}/quiz10/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 10: Yakuniy bosqich!\n"
                "========================================\n"
                "🎯 Mavzu: Yakuniy sinov\n\n"
                "📝 Vazifa:\n"
                "  1) 'final.sh' skriptiga ishga tushirish huquqini bering\n"
                "  2) Skriptni ishga tushiring\n"
                "  3) 'check' buyrug'ini bering va o'zingizning g'oliblik FLAG'ingizni oling!\n\n"
                "💡 Foydalanishingiz mumkin bo'lgan buyruqlar:\n"
                "  Bu yerda 'chmod', 'ls', './' buyruqlaridan foydalanishingiz mumkin.\n\n"
                "✅ Tekshirish:\n"
                "  Bajarib bo'lgach, terminalda tekshiring:\n"
                "  check\n"
                "========================================"
            )
        }
        fs[f"/home/{username}/quiz10/final.sh"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "#!/bin/bash\n"
                "DIR=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd)\"\n"
                "echo \"Tabriklaymiz, siz oxirgi bosqichga yetdingiz!\" > \"$DIR/result.txt\"\n"
                "echo \"SUCCESS: result.txt created!\""
            )
        }


def _populate_ctf2_fs(fs, username, stage, answers):
    # ═════════════════════════════════════════════════════════
    # ── CTF 2: CHUQURLASHTIRILGAN BOSQICHLAR (1-10) ──────────
    # ═════════════════════════════════════════════════════════
    fs[f"/home/{username}/ROADMAP.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================================================\n"
                "🔥 CTF 2: ILG'OR TIZIM & KIBERXAVFSIZLIK ROADMAP 🔥\n"
                "========================================================================\n\n"
                "📌 ASOSIY BUYRUQLAR:\n"
                "  • check   - Joriy bosqichdagi vazifangiz to'g'ri bajarilganini tekshiradi.\n"
                "  • status  - Hozir qaysi bosqichda ekanligingiz va vazifa shartini ko'rsatadi.\n\n"
                "🗺 CTF 2 BOSQICHLARI (1-10):\n"
                "   1. quiz1  | chmod, cd            | Yopiq secret_zone papkasiga kirish ruxsatini to'g'rilash\n"
                "   2. quiz2  | chmod, cat           | O'qish huquqi cheklangan confidential.txt ni o'qish\n"
                "   3. quiz3  | grep -w              | Yuzlab soxta so'zlar orasidan mustaqil BiGs0Z ni topish\n"
                "   4. quiz4  | grep -i, grep -v     | Logdagi shovqinlarni filtrlab auth_token ni ajratish\n"
                "   5. quiz5  | find -size           | storage/ dan aynan 1024 baytli faylni qidirib topish\n"
                "   6. quiz6  | find -perm           | 777 ruxsatli xavfli ochiq faylni aniqlash\n"
                "   7. quiz7  | find -type           | archive/ dan katalog emas, aynan oddiy faylni ajratish\n"
                "   8. quiz8  | grep -n              | Kalit qaysi qatorda turganini raqam bilan aniqlash\n"
                "   9. quiz9  | find, rm             | Bo'sh fayllar orasidan ma'lumotli haqiqiy faylni topish\n"
                "  10. quiz10 | CTF 2 Final          | Final Lockbox: chmod + find + grep va 2-FLAG! 🏆\n\n"
                "🚀 Boshlash uchun:\n"
                "  cd ~/quiz1\n"
                "  cat README.txt\n\n"
                "Omad tilaymiz!\n"
                "========================================================================"
            )
        }

    # ── quiz1: chmod katalogga kirish ──
    if stage >= 1:
        k11 = answers.get(11, "SEC11-DEFAULT")
        fs[f"/home/{username}/quiz1"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["README.txt", "secret_zone"]
        }
        fs[f"/home/{username}/quiz1/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 1: Yopiq katalogga kirish (Permissions)\n"
                "========================================\n"
                "🎯 Mavzu: chmod, ls -la, cd\n\n"
                "📝 Vazifa:\n"
                "  Ushbu papkada 'secret_zone' katalogi mavjud, ammo hozirda unga kirib bo'lmayapti\n"
                "  (Permission denied).\n"
                "  1) Katalog ruxsatlarini tahlil qiling va unga kirish huquqini bering\n"
                "  2) Uning ichidagi yashirin '.secret_flag' faylini topib,\n"
                "     uning ichidagi kalitni 'answer.txt' nomli faylga yozing.\n\n"
                "✅ Tekshirish: check\n"
                "========================================"
            )
        }
        fs[f"/home/{username}/quiz1/secret_zone"] = {
            "type": "dir", "owner": username, "mode": "000",
            "children": [".secret_flag"]
        }
        fs[f"/home/{username}/quiz1/secret_zone/.secret_flag"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": k11
        }

    # ── quiz2: chmod faylni o'qish ──
    if stage >= 2:
        k12 = answers.get(12, "CONF12-DEFAULT")
        fs[f"/home/{username}/quiz2"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["README.txt", "confidential.txt"]
        }
        fs[f"/home/{username}/quiz2/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 2: O'qish huquqi cheklangan fayl\n"
                "========================================\n"
                "🎯 Mavzu: chmod, cat\n\n"
                "📝 Vazifa:\n"
                "  'confidential.txt' fayli o'qish uchun bloklangan (ruxsat yo'q).\n"
                "  Unga o'qish huquqini bering va undagi maxfiy kalitni\n"
                "  'answer.txt' fayliga saqlang.\n\n"
                "✅ Tekshirish: check\n"
                "========================================"
            )
        }
        fs[f"/home/{username}/quiz2/confidential.txt"] = {
            "type": "file", "owner": username, "mode": "200",
            "content": k12
        }

    # ── quiz3: grep -w va -n (so'z va qator raqami) ──
    if stage >= 3:
        fake_words = [
            "not_BiGs0Z", "BiGs0Z_fake", "testBiGs0Z123", "fake_BiGs0Z_word",
            "BiGs0Z_old", "BiGs0Zextra", "sample_BiGs0Z", "BiGs0Z_v2",
            "system_BiGs0Z", "BiGs0Z_archive", "temp_BiGs0Z_log", "BiGs0Z_dummy"
        ]
        lines = []
        for i in range(1, 40):
            lines.append(fake_words[i % len(fake_words)])
        lines.insert(22, "BiGs0Z")
        for i in range(41, 70):
            lines.append(fake_words[i % len(fake_words)])

        fs[f"/home/{username}/quiz3"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["README.txt", "mixed_words.txt"]
        }
        fs[f"/home/{username}/quiz3/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 3: Aniq so'zni va uning qator raqamini topish\n"
                "========================================\n"
                "📝 Vazifa:\n"
                "  'mixed_words.txt' ichida yuzlab o'xshash soxta so'zlar bor.\n"
                "  Sizga aynan kerakli so'z: 'BiGs0Z'\n"
                "  Ushbu mustaqil 'BiGs0Z' so'zi faylning nechanchi qatorida\n"
                "  joylashganini aniqlang va o'sha qator raqamini 'answer.txt' fayliga yozing.\n\n"
                "✅ Tekshirish: check\n"
                "========================================"
            )
        }
        fs[f"/home/{username}/quiz3/mixed_words.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": "\n".join(lines)
        }

    # ── quiz4: grep -i va grep -v ──
    if stage >= 4:
        k14 = answers.get(14, "LOG14-DEFAULT")
        log_entries = []
        for i in range(1, 60):
            log_entries.append(f"2026-09-09 10:{i:02d}:00 [DEBUG] system check {i} - status OK, no anomaly")
        log_entries.insert(33, f"2026-09-09 10:33:12 [INFO] AuTh_ToKeN: {k14}")
        for i in range(61, 100):
            log_entries.append(f"2026-09-09 11:{i%60:02d}:00 [DEBUG] routine log {i} - normal state")

        fs[f"/home/{username}/quiz4"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["README.txt", "server_log.txt"]
        }
        fs[f"/home/{username}/quiz4/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 4: Shovqin va registr tahlili\n"
                "========================================\n"
                "🎯 Mavzu: grep\n\n"
                "📝 Vazifa:\n"
                "  'server_log.txt' faylida yuzlab DEBUG shovqinlari mavjud.\n"
                "  Fayldagi maxfiy auth_token qiymatini (registrga qaramay yoki shovqinni inkor qilib)\n"
                "  aniqlang va uni 'answer.txt' fayliga yozing.\n\n"
                "✅ Tekshirish: check\n"
                "========================================"
            )
        }
        fs[f"/home/{username}/quiz4/server_log.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": "\n".join(log_entries)
        }

    # ── quiz5: find -size ──
    if stage >= 5:
        k15 = answers.get(15, "SIZE15-DEFAULT")
        storage_children = []
        for i in range(1, 21):
            fname = f"chunk_{i:02d}.dat"
            storage_children.append(fname)
            cnt = "x" * (i * 45)
            fs[f"/home/{username}/quiz5/storage/{fname}"] = {
                "type": "file", "owner": username, "mode": "644", "content": cnt
            }
        exact_fname = "target_package.bin"
        storage_children.append(exact_fname)
        exact_content = f"{k15}\n" + ("A" * (1024 - len(k15) - 1))
        fs[f"/home/{username}/quiz5/storage/{exact_fname}"] = {
            "type": "file", "owner": username, "mode": "644", "content": exact_content
        }

        fs[f"/home/{username}/quiz5"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["README.txt", "storage"]
        }
        fs[f"/home/{username}/quiz5/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 5: Fayl hajmi bo'yicha qidiruv\n"
                "========================================\n"
                "🎯 Mavzu: find\n\n"
                "📝 Vazifa:\n"
                "  'storage/' katalogida 20 dan ortiq fayl mavjud.\n"
                "  Ularning orasidan hajmi AYNAN 1024 bayt bo'lgan faylni toping.\n"
                "  Uning ichidagi birinchi qatorda turgan kalitni 'answer.txt' ga yozing.\n\n"
                "✅ Tekshirish: check\n"
                "========================================"
            )
        }
        fs[f"/home/{username}/quiz5/storage"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": storage_children
        }

    # ── quiz6: find -perm ──
    if stage >= 6:
        k16 = answers.get(16, "PERM16-DEFAULT")
        restricted_children = []
        for i in range(1, 15):
            fname = f"secure_item_{i:02d}.conf"
            restricted_children.append(fname)
            fs[f"/home/{username}/quiz6/restricted/{fname}"] = {
                "type": "file", "owner": username, "mode": "640", "content": f"safe config {i}"
            }
        danger_fname = "insecure_node.cfg"
        restricted_children.append(danger_fname)
        fs[f"/home/{username}/quiz6/restricted/{danger_fname}"] = {
            "type": "file", "owner": username, "mode": "777", "content": k16
        }

        fs[f"/home/{username}/quiz6"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["README.txt", "restricted"]
        }
        fs[f"/home/{username}/quiz6/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 6: Huquqi bo'yicha qidiruv\n"
                "========================================\n"
                "🎯 Mavzu: find\n\n"
                "📝 Vazifa:\n"
                "  'restricted/' papkasidagi fayllar orasidan xavfli 777 (rwxrwxrwx) ruxsatga\n"
                "  ega bo'lgan faylni aniqlang va undagi kalitni 'answer.txt' ga yozing.\n\n"
                "✅ Tekshirish: check\n"
                "========================================"
            )
        }
        fs[f"/home/{username}/quiz6/restricted"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": restricted_children
        }

    # ── quiz7: find -type (labirint va soxta kataloglar) ──
    if stage >= 7:
        k17 = answers.get(17, "TYPE17-DEFAULT")
        fs[f"/home/{username}/quiz7"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["README.txt", "archive"]
        }
        fs[f"/home/{username}/quiz7/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 7: Turi bo'yicha ajratish (Find by type)\n"
                "========================================\n"
                "🎯 Mavzu: find\n\n"
                "📝 Vazifa:\n"
                "  'archive/' katalogida o'nlab ichma-ich papkalar va soxta obyektlar bor.\n"
                "  Tizimda 'vault_data' nomli bir nechta papkalar ham mavjud bo'lib, ular sizni chalg'itadi.\n"
                "  Siz aynan oddiy fayl (file) turiga tegishli 'vault_data' ni topishingiz\n"
                "  va undagi maxfiy kalitni 'answer.txt' ga ko'chirishingiz kerak.\n\n"
                "✅ Tekshirish: check\n"
                "========================================"
            )
        }
        # Labirint strukturasi
        fs[f"/home/{username}/quiz7/archive"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["backup", "temp", "storage", "vault_data", "logs"]
        }
        # 1-soxta: archive/vault_data bu katalog!
        fs[f"/home/{username}/quiz7/archive/vault_data"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["dummy.txt"]
        }
        fs[f"/home/{username}/quiz7/archive/vault_data/dummy.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": "Bu papka, sizga oddiy fayl kerak edi!"
        }

        # archive/backup
        fs[f"/home/{username}/quiz7/archive/backup"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["daily", "weekly", "vault_data"]
        }
        # 2-soxta: archive/backup/vault_data bu ham katalog!
        fs[f"/home/{username}/quiz7/archive/backup/vault_data"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["old.log"]
        }
        fs[f"/home/{username}/quiz7/archive/backup/vault_data/old.log"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": "Bu ham papka!"
        }
        fs[f"/home/{username}/quiz7/archive/backup/daily"] = {
            "type": "dir", "owner": username, "mode": "755", "children": ["data1.tar"]
        }
        fs[f"/home/{username}/quiz7/archive/backup/daily/data1.tar"] = {
            "type": "file", "owner": username, "mode": "644", "content": "tar archive"
        }
        fs[f"/home/{username}/quiz7/archive/backup/weekly"] = {
            "type": "dir", "owner": username, "mode": "755", "children": []
        }

        # archive/temp
        fs[f"/home/{username}/quiz7/archive/temp"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["cache", "session_dump"]
        }
        fs[f"/home/{username}/quiz7/archive/temp/cache"] = {
            "type": "dir", "owner": username, "mode": "755", "children": []
        }
        fs[f"/home/{username}/quiz7/archive/temp/session_dump"] = {
            "type": "file", "owner": username, "mode": "644", "content": "empty cache"
        }

        # archive/logs
        fs[f"/home/{username}/quiz7/archive/logs"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["syslog.1", "vault_data"]
        }
        fs[f"/home/{username}/quiz7/archive/logs/syslog.1"] = {
            "type": "file", "owner": username, "mode": "644", "content": "system logs"
        }
        # 3-soxta: archive/logs/vault_data bu ham katalog!
        fs[f"/home/{username}/quiz7/archive/logs/vault_data"] = {
            "type": "dir", "owner": username, "mode": "755", "children": []
        }

        # archive/storage/deep/nested/... -> haqiqiy fayl!
        fs[f"/home/{username}/quiz7/archive/storage"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["zone_a", "zone_b"]
        }
        fs[f"/home/{username}/quiz7/archive/storage/zone_a"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["cluster1"]
        }
        fs[f"/home/{username}/quiz7/archive/storage/zone_a/cluster1"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["node_info.txt"]
        }
        fs[f"/home/{username}/quiz7/archive/storage/zone_a/cluster1/node_info.txt"] = {
            "type": "file", "owner": username, "mode": "644", "content": "cluster node"
        }

        fs[f"/home/{username}/quiz7/archive/storage/zone_b"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["secured_core"]
        }
        fs[f"/home/{username}/quiz7/archive/storage/zone_b/secured_core"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["vault_data"]
        }
        # HAQIQIY FAYL!
        fs[f"/home/{username}/quiz7/archive/storage/zone_b/secured_core/vault_data"] = {
            "type": "file", "owner": username, "mode": "644", "content": k17
        }

    # ── quiz8: grep -n va wc -l (qator va umumiy hajm tahlili) ──
    if stage >= 8:
        k18 = answers.get(18, "LINE18-DEFAULT")
        line_entries = []
        for i in range(1, 345):
            line_entries.append(f"satr #{i} - odatiy ma'lumot")
        line_entries.append(f"TARGET_SECRET: {k18}")
        for i in range(346, 501):
            line_entries.append(f"satr #{i} - odatiy ma'lumot")

        fs[f"/home/{username}/quiz8"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["README.txt", "lines.txt"]
        }
        fs[f"/home/{username}/quiz8/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 8: Qator tahlili (grep va wc)\n"
                "========================================\n"
                "🎯 Mavzu: grep, wc\n\n"
                "📝 Vazifa:\n"
                "  Siz avvalroq so'z turgan qator raqamini aniqlashni o'rgangan edingiz.\n"
                "  Endi 'lines.txt' fayli ichidagi ma'lumotlarni tahlil qiling:\n"
                "  1) 'TARGET_SECRET' so'zi nechanchi qatorda turganini aniqlang\n"
                "  2) 'lines.txt' faylida jami (umumiy) nechta qator borligini aniqlang\n"
                "  3) Javobni 'answer.txt' fayliga quyidagi formatda yozing:\n"
                "     NISHON_QATORI|UMUMIY_QATORLAR\n"
                "     (Masalan, agar 120-qatorda bo'lsa va jami 300 qator bo'lsa: 120|300)\n\n"
                "💡 Eslatma: O'rtada vertikal chiziqcha (|) bo'lishi shart.\n"
                "✅ Tekshirish: check\n"
                "========================================"
            )
        }
        fs[f"/home/{username}/quiz8/lines.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": "\n".join(line_entries)
        }

    # ── quiz9: bo'sh fayllarni saralash ──
    if stage >= 9:
        k19 = answers.get(19, "CLEAN19-DEFAULT")
        cleanup_children = []
        for i in range(1, 21):
            fname = f"empty_{i:02d}.log"
            cleanup_children.append(fname)
            # 13-fayl bo'sh emas, aynan uning ichida haqiqiy kalit bor!
            cnt = k19 if i == 13 else ""
            fs[f"/home/{username}/quiz9/cleanup/{fname}"] = {
                "type": "file", "owner": username, "mode": "644", "content": cnt
            }

        fs[f"/home/{username}/quiz9"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["README.txt", "cleanup"]
        }
        fs[f"/home/{username}/quiz9/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 9: Bo'sh fayllarni tozalash (Cleanup)\n"
                "========================================\n"
                "🎯 Mavzu: find, cat\n\n"
                "📝 Vazifa:\n"
                "  'cleanup/' papkasi 20 ta bo'sh fayl bilan to'ldirilgan.\n"
                "  Haqiqiy ma'lumotga ega yagona faylni aniqlang va undagi kalitni 'answer.txt' ga yozing.\n\n"
                "✅ Tekshirish: check\n"
                "========================================"
            )
        }
        fs[f"/home/{username}/quiz9/cleanup"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": cleanup_children
        }

    # ── quiz10: final lockbox ──
    if stage >= 10:
        k20 = answers.get(20, "FINAL20-DEFAULT")
        lockbox_children = []
        for i in range(1, 10):
            fname = f"box_{i:02d}.bin"
            lockbox_children.append(fname)
            fs[f"/home/{username}/quiz10/lockbox/{fname}"] = {
                "type": "file", "owner": username, "mode": "644", "content": "0" * (i * 50)
            }
        exact_512 = f"FINAL_FLAG: {k20}\n" + ("Z" * (512 - len(f"FINAL_FLAG: {k20}\n")))
        lockbox_children.append("box_10.bin")
        fs[f"/home/{username}/quiz10/lockbox/box_10.bin"] = {
            "type": "file", "owner": username, "mode": "644", "content": exact_512
        }

        fs[f"/home/{username}/quiz10"] = {
            "type": "dir", "owner": username, "mode": "755",
            "children": ["README.txt", "lockbox"]
        }
        fs[f"/home/{username}/quiz10/README.txt"] = {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================\n"
                "📌 QUIZ 10: CTF 2 Yakuniy Sinov (Final Lockbox)\n"
                "========================================\n"
                "🎯 Mavzu: chmod, find, grep\n\n"
                "📝 Vazifa:\n"
                "  1) 'lockbox/' katalogiga kirish huquqini bering\n"
                "  2) Uning ichidagi aynan 512 bayt bo'lgan faylni toping\n"
                "  3) Fayl ichidagi 'FINAL_FLAG: ...' qatoridan kalitni olib 'answer.txt' ga yozing\n"
                "  4) 'check' deb tekshirib, CTF 2 g'oliblik flagini oling!\n\n"
                "✅ Tekshirish: check\n"
                "========================================"
            )
        }
        fs[f"/home/{username}/quiz10/lockbox"] = {
            "type": "dir", "owner": username, "mode": "000",
            "children": lockbox_children
        }

    return fs


USER_FILESYSTEMS = {}


def get_fs(username):
    if username not in USER_FILESYSTEMS:
        saved = db.load_user_vfs(username)
        if saved:
            USER_FILESYSTEMS[username] = saved
        else:
            USER_FILESYSTEMS[username] = get_user_fs(username)
            db.save_user_vfs(username, USER_FILESYSTEMS[username])
    return USER_FILESYSTEMS[username]


def sync_fs(username):
    USER_FILESYSTEMS[username] = get_user_fs(username)
    db.save_user_vfs(username, USER_FILESYSTEMS[username])
    return USER_FILESYSTEMS[username]


@app.route("/login")
def login_page():
    if session.get("username"):
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    result = db.register_user(username, password)
    if result["ok"]:
        # Auto-login after registration
        session.permanent = True
        session["username"] = username
        sync_fs(username)
    return jsonify(result)


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    result = db.login_user(username, password)
    if result["ok"]:
        session.permanent = True
        session["username"] = username
        sync_fs(username)
    return jsonify(result)


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    username = session.get("username")
    if not username:
        return jsonify({"logged_in": False}), 401
    stage = db.get_student_stage(username)
    return jsonify({"logged_in": True, "username": username, "stage": stage})


@app.route("/")
@login_required
def index():
    username = session.get("username")
    db.seed_student(username)
    status = db.get_student_ctf_status(username)
    stage = status["ctf2_stage"] if status["active_ctf"] == 2 else status["ctf1_stage"]
    if stage <= 10:
        db.record_stage_start(username, status["active_ctf"], stage)
    return render_template(
        "index.html",
        username=username,
        stage=stage,
        active_ctf=status["active_ctf"],
        ctf1_stage=status["ctf1_stage"],
        ctf2_stage=status["ctf2_stage"],
        ctf2_unlocked=status["ctf2_unlocked"]
    )


@app.route("/api/ctf_status", methods=["GET"])
@login_required
def get_ctf_status():
    username = session.get("username", "talaba1")
    status = db.get_student_ctf_status(username)
    stage = status["ctf2_stage"] if status["active_ctf"] == 2 else status["ctf1_stage"]
    return jsonify({
        "username": username,
        "active_ctf": status["active_ctf"],
        "stage": stage,
        "ctf1_stage": status["ctf1_stage"],
        "ctf2_stage": status["ctf2_stage"],
        "ctf2_unlocked": status["ctf2_unlocked"]
    })


@app.route("/api/switch_ctf", methods=["POST"])
@login_required
def switch_ctf():
    data = request.json or {}
    target_ctf = data.get("ctf", 1)
    username = session.get("username", "talaba1")
    res = db.switch_active_ctf(username, target_ctf)
    if not res["ok"]:
        return jsonify(res), 403
    sync_fs(username)
    status = db.get_student_ctf_status(username)
    stage = status["ctf2_stage"] if status["active_ctf"] == 2 else status["ctf1_stage"]
    if stage <= 10:
        db.record_stage_start(username, status["active_ctf"], stage)
    return jsonify({
        "ok": True,
        "active_ctf": status["active_ctf"],
        "stage": stage,
        "ctf1_stage": status["ctf1_stage"],
        "ctf2_stage": status["ctf2_stage"],
        "ctf2_unlocked": status["ctf2_unlocked"]
    })


@app.route("/api/status", methods=["GET"])
@login_required
def get_status():
    username = session.get("username", "talaba1")
    status = db.get_student_ctf_status(username)
    active_ctf = status["active_ctf"]
    stage = status["ctf2_stage"] if active_ctf == 2 else status["ctf1_stage"]
    quiz_dict = QUIZZES_CTF2 if active_ctf == 2 else QUIZZES_CTF1
    quiz_info = quiz_dict.get(stage, {
        "title": "Tugallangan",
        "description": "Barcha 10 ta bosqich muvaffaqiyatli topshirildi!"
    })
    return jsonify({
        "username": username,
        "active_ctf": active_ctf,
        "current_stage": stage,
        "quiz": quiz_info,
        "completed": stage > 10,
        "status": status
    })


@app.route("/api/leaderboard", methods=["GET"])
@login_required
def get_leaderboard_data():
    board = db.get_leaderboard()
    return jsonify({"leaderboard": board})


@app.route("/api/reset", methods=["POST"])
@login_required
def reset_progress():
    username = session.get("username", "talaba1")
    db.reset_student(username)
    sync_fs(username)
    return jsonify({"status": "ok", "message": f"{username} muvaffaqiyatli qayta tiklandi (Stage 1)."})


# ── Admin Panel Routes ──────────────────────────────────────────────

ADMIN_SECRET_KEY = os.environ.get("ADMIN_KEY", "admin123")


def is_admin_session():
    return session.get("is_admin") is True or session.get("username") in ("admin", "ustoz")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_admin_session():
            if request.is_json:
                return jsonify({"error": "unauthorized", "message": "Admin ruxsati talab qilinadi"}), 403
            return redirect(url_for("admin_page"))
        return f(*args, **kwargs)
    return decorated


@app.route("/admin")
def admin_page():
    return render_template("admin.html", is_admin=is_admin_session())


@app.route("/api/admin/login", methods=["POST"])
def admin_login_api():
    data = request.json or {}
    key = data.get("password", "").strip()
    if key == ADMIN_SECRET_KEY or key == "admin2026" or (session.get("username") in ("admin", "ustoz")):
        session["is_admin"] = True
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Admin paroli noto'g'ri!"}), 401


@app.route("/api/admin/logout", methods=["POST"])
def admin_logout_api():
    session.pop("is_admin", None)
    return jsonify({"ok": True})


@app.route("/api/admin/overview", methods=["GET"])
@admin_required
def admin_overview_api():
    return jsonify(db.get_admin_overview())


@app.route("/api/admin/users", methods=["GET"])
@admin_required
def admin_users_api():
    users = db.get_admin_users()
    return jsonify({"users": users})


@app.route("/api/admin/user/<target_user>/audit", methods=["GET"])
@admin_required
def admin_user_audit_api(target_user):
    detail = db.get_student_audit_detail(target_user, QUIZZES_CTF1, QUIZZES_CTF2)
    if not detail:
        return jsonify({"error": "Foydalanuvchi topilmadi"}), 404
    return jsonify(detail)


@app.route("/api/admin/user/<target_user>/reset", methods=["POST"])
@admin_required
def admin_user_reset_api(target_user):
    db.reset_student(target_user)
    sync_fs(target_user)
    return jsonify({"ok": True, "message": f"{target_user} statistikasi va bosqichlari qayta tiklandi."})


@app.route("/api/file/read", methods=["POST"])
@login_required
def read_file():
    data = request.json or {}
    path = data.get("path", "").replace("\\", "/")
    username = session.get("username", "talaba1")
    fs = get_fs(username)
    if path in fs and fs[path]["type"] == "file":
        return jsonify({"status": "ok", "content": fs[path]["content"]})
    return jsonify({"status": "error", "message": f"Fayl topilmadi: {path}"}), 404


@app.route("/api/file/write", methods=["POST"])
@login_required
def save_file():
    data = request.json or {}
    path = data.get("path", "").replace("\\", "/")
    content = data.get("content", "")
    username = session.get("username", "talaba1")
    fs = get_fs(username)

    parent_dir = posixpath.dirname(path)
    if parent_dir not in fs or fs[parent_dir]["type"] != "dir":
        return jsonify({"status": "error", "message": f"Papka mavjud emas: {parent_dir}"}), 400

    filename = posixpath.basename(path)
    if filename not in fs[parent_dir]["children"]:
        fs[parent_dir]["children"].append(filename)

    fs[path] = {"type": "file", "owner": username, "mode": "644", "content": content}
    db.save_user_vfs(username, fs)
    return jsonify({"status": "ok", "message": f"Fayl saqlandi: {path}"})


@app.route("/api/check", methods=["POST"])
@login_required
def check_quiz():
    username = session.get("username", "talaba1")
    ctf_status = db.get_student_ctf_status(username)
    active_ctf = ctf_status["active_ctf"]
    stage = ctf_status["ctf2_stage"] if active_ctf == 2 else ctf_status["ctf1_stage"]
    fs = get_fs(username)

    if stage > 10:
        ctf_label = "CTF 1 (Linux Asoslari)" if active_ctf == 1 else "CTF 2 (Ilg'or Kiberxavfsizlik)"
        return jsonify({
            "status": "pass",
            "stage": stage,
            "message": f"🎉 Siz {ctf_label} ning barcha 10 ta bosqichini to'liq tugatgansiz! Leaderboard'dan o'z flagingizni ko'rishingiz mumkin."
        })

    passed = False

    if active_ctf == 1:
        # ── CTF 1 Checks (1-10) ──────────────────────────────────
        if stage == 1:
            d1 = f"/home/{username}/quiz1/images"
            d2 = f"/home/{username}/quiz1/docs"
            d3 = f"/home/{username}/quiz1/documents"
            if (d1 in fs and fs[d1]["type"] == "dir" and
                    d2 in fs and fs[d2]["type"] == "dir" and
                    d3 in fs and fs[d3]["type"] == "dir"):
                passed = True

        elif stage == 2:
            f1 = f"/home/{username}/quiz2/docs/notes.txt"
            f2 = f"/home/{username}/quiz2/docs/todo.txt"
            if (f1 in fs and fs[f1]["type"] == "file" and
                    f2 in fs and fs[f2]["type"] == "file"):
                passed = True

        elif stage == 3:
            f = f"/home/{username}/quiz3/notes.txt"
            if f in fs and fs[f]["type"] == "file" and "linux200" in fs[f]["content"]:
                passed = True

        elif stage == 4:
            f = f"/home/{username}/quiz4/answer.txt"
            expected = db.get_student_answers(username).get(4, "")
            if f in fs and fs[f]["type"] == "file":
                given = fs[f]["content"].strip().replace(" ", "").replace("\n", "")
                if expected in given:
                    passed = True

        elif stage == 5:
            f = f"/home/{username}/quiz5/answer.txt"
            expected = db.get_student_answers(username).get(5, "")
            if f in fs and fs[f]["type"] == "file":
                given = fs[f]["content"].strip().replace(" ", "").replace("\n", "")
                if expected in given:
                    passed = True

        elif stage == 6:
            req = f"/home/{username}/quiz6/required.txt"
            t1 = f"/home/{username}/quiz6/temp1.txt"
            t2 = f"/home/{username}/quiz6/temp2.txt"
            junk = f"/home/{username}/quiz6/junk"
            if req in fs and t1 not in fs and t2 not in fs and junk not in fs:
                passed = True

        elif stage == 7:
            s = f"/home/{username}/quiz7/script.sh"
            d = f"/home/{username}/quiz7/done.txt"
            mode = fs.get(s, {}).get("mode", "644")
            is_exec = ("x" in mode or mode in ("755", "777", "775", "111"))
            if s in fs and is_exec and d in fs and fs[d]["type"] == "file":
                passed = True

        elif stage == 8:
            sec = f"/home/{username}/quiz8/secret.txt"
            if sec in fs and fs[sec]["owner"] == username:
                passed = True

        elif stage == 9:
            f = f"/home/{username}/quiz9/answer.txt"
            expected = db.get_student_answers(username).get(9, "")
            if f in fs and fs[f]["type"] == "file":
                given = fs[f]["content"].strip().replace(" ", "").replace("\n", "")
                if given == expected:
                    passed = True

        elif stage == 10:
            fin = f"/home/{username}/quiz10/final.sh"
            res = f"/home/{username}/quiz10/result.txt"
            mode = fs.get(fin, {}).get("mode", "644")
            is_exec = ("x" in mode or mode in ("755", "777", "775", "111"))
            if fin in fs and is_exec and res in fs and fs[res]["type"] == "file":
                passed = True

    else:
        # ── CTF 2 Checks (1-10) ──────────────────────────────────
        def get_answer_content(st):
            # Check ~/quiz{st}/answer.txt as well as any subdirectories like ~/quiz{st}/*/answer.txt
            base_f = f"/home/{username}/quiz{st}/answer.txt"
            if base_f in fs and fs[base_f]["type"] == "file":
                return fs[base_f]["content"].strip().replace(" ", "").replace("\n", "")
            # search subdirectories of quiz{st}
            for path_k, item in fs.items():
                if path_k.startswith(f"/home/{username}/quiz{st}/") and path_k.endswith("/answer.txt"):
                    if item["type"] == "file":
                        return item["content"].strip().replace(" ", "").replace("\n", "")
            return None

        # quiz1: secret_zone papkasiga execute ruxsati berilgan va .secret_flag kaliti ko'chirilgan
        if stage == 1:
            expected = db.get_student_answers(username).get(11, "")
            mode_dir = fs.get(f"/home/{username}/quiz1/secret_zone", {}).get("mode", "000")
            has_exec = ("x" in mode_dir or mode_dir in ("755", "777", "775", "111", "555"))
            given = get_answer_content(1)
            if given and has_exec and expected in given:
                passed = True

        # quiz2: confidential.txt ga read ruxsati berilgan va kalit ko'chirilgan
        elif stage == 2:
            f = f"/home/{username}/quiz2/answer.txt"
            expected = db.get_student_answers(username).get(12, "")
            mode_file = fs.get(f"/home/{username}/quiz2/confidential.txt", {}).get("mode", "200")
            has_read = ("r" in mode_file or "x" in mode_file or mode_file in ("644", "755", "777", "444", "666", "x"))
            if f in fs and fs[f]["type"] == "file" and has_read:
                given = fs[f]["content"].strip().replace(" ", "").replace("\n", "")
                if expected in given:
                    passed = True

        # quiz3: mixed_words.txt dan to'liq so'z BiGs0Z qator raqami (23) topilgan
        elif stage == 3:
            f = f"/home/{username}/quiz3/answer.txt"
            if f in fs and fs[f]["type"] == "file":
                given = fs[f]["content"].strip().replace(" ", "").replace("\n", "")
                # 23 (qator raqami) yoki BiGs0Z bo'lsa ham qabul qilamiz
                if "23" in given or "BiGs0Z" in given:
                    passed = True

        # quiz4: server_log.txt dan auth_token topilgan
        elif stage == 4:
            f = f"/home/{username}/quiz4/answer.txt"
            expected = db.get_student_answers(username).get(14, "")
            if f in fs and fs[f]["type"] == "file":
                given = fs[f]["content"].strip().replace(" ", "").replace("\n", "")
                if expected in given:
                    passed = True

        # quiz5: storage/ dan 1024 baytli fayl kaliti topilgan
        elif stage == 5:
            f = f"/home/{username}/quiz5/answer.txt"
            expected = db.get_student_answers(username).get(15, "")
            if f in fs and fs[f]["type"] == "file":
                given = fs[f]["content"].strip().replace(" ", "").replace("\n", "")
                if expected in given:
                    passed = True

        # quiz6: restricted/ dan 777 ruxsatli fayl kaliti topilgan
        elif stage == 6:
            f = f"/home/{username}/quiz6/answer.txt"
            expected = db.get_student_answers(username).get(16, "")
            if f in fs and fs[f]["type"] == "file":
                given = fs[f]["content"].strip().replace(" ", "").replace("\n", "")
                if expected in given:
                    passed = True

        # quiz7: archive/ dan oddiy fayl kaliti topilgan
        elif stage == 7:
            f = f"/home/{username}/quiz7/answer.txt"
            expected = db.get_student_answers(username).get(17, "")
            if f in fs and fs[f]["type"] == "file":
                given = fs[f]["content"].strip().replace(" ", "").replace("\n", "")
                if expected in given:
                    passed = True

        # quiz8: lines.txt da TARGET_SECRET qatori va umumiy qatorlar: 345|500
        elif stage == 8:
            f = f"/home/{username}/quiz8/answer.txt"
            if f in fs and fs[f]["type"] == "file":
                given = fs[f]["content"].strip().replace(" ", "").replace("\n", "")
                if "345|500" in given or "345:500" in given:
                    passed = True

        # quiz9: cleanup/ dan bo'sh bo'lmagan fayl kaliti topilgan
        elif stage == 9:
            expected = db.get_student_answers(username).get(19, "")
            given = get_answer_content(9)
            if given and expected in given:
                passed = True

        # quiz10: lockbox ruxsati ochilgan va final kalit topilgan
        elif stage == 10:
            expected = db.get_student_answers(username).get(20, "")
            mode_box = fs.get(f"/home/{username}/quiz10/lockbox", {}).get("mode", "000")
            has_exec = ("x" in mode_box or mode_box in ("755", "777", "775", "111", "555"))
            given = get_answer_content(10)
            if given and has_exec and expected in given:
                passed = True

    if passed:
        fail_cnt = db.get_stage_fail_count(username, stage, ctf=active_ctf)
        score_awarded = 1 if fail_cnt <= 3 else 0
        db.record_stage_finish(username, active_ctf, stage)
        db.record_stage_score(username, active_ctf, stage, score_awarded)
        db.log_attempt(username, stage, "pass", ctf=active_ctf)

        next_stage = stage + 1
        db.update_student_stage(username, next_stage)
        db.record_stage_start(username, active_ctf, next_stage)
        sync_fs(username)

        score_note = "⭐ A'lo! Bosqich mustaqil yechildi (+1 ball)!" if score_awarded == 1 else "⚠️ Kalit qabul qilindi, ammo ko'p urinish/maslahat tufayli ball berilmadi (0 ball)."

        # CTF 1 yakunlangan holat (Stage 10 muvaffaqiyatli topshirildi)
        if active_ctf == 1 and stage == 10:
            secret1 = "CTF1_SECRET_KEY_2026"
            flag1_hash = hashlib.sha256(f"{username}{secret1}".encode()).hexdigest()[:20]
            flag1 = f"CTF1{{{flag1_hash}}}"
            db.save_student_flag(username, flag1, level=1)
            return jsonify({
                "status": "pass",
                "next_stage": 11,
                "ctf1_completed": True,
                "ctf2_unlocked": True,
                "message": (
                    "========================================================\n"
                    "🎉🎉🎉 TABRIKLAYMIZ! SIZ CTF 1'NI TO'LIQ TUGATDINGIZ! 🎉🎉🎉\n"
                    f"{score_note}\n\n"
                    f"Sizning 1-bosqich flag'ingiz:\n\n"
                    f"    {flag1}\n\n"
                    "🔓 SIZGA CTF 2 (ILG'OR KIBERXAVFSIZLIK) OCHILDI!\n"
                    "Yuqoridagi menyudan '🛡️ CTF 2' tugmasini bosing yoki\n"
                    "terminalda 'ctf2' deb yozib, 2-bosqichlarni boshlang!\n"
                    "========================================================"
                )
            })

        # CTF 2 yakunlangan holat (Stage 10 muvaffaqiyatli topshirildi)
        elif active_ctf == 2 and stage == 10:
            secret2 = "CTF2_SECRET_KEY_2026"
            flag2_hash = hashlib.sha256(f"{username}{secret2}".encode()).hexdigest()[:20]
            flag2 = f"CTF2{{{flag2_hash}}}"
            db.save_student_flag(username, flag2, level=2)
            return jsonify({
                "status": "completed",
                "next_stage": 11,
                "message": (
                    "====================================================================\n"
                    "👑👑👑 SIZ CTF 2'NI VA BUTUN CTF PLATFORMASINI TO'LIQ ZABT ETDINGIZ! 👑👑👑\n"
                    f"{score_note}\n\n"
                    f"Sizning Final CTF 2 Flag'ingiz:\n\n"
                    f"    {flag2}\n\n"
                    "🏆 Siz haqiqiy Linux va Kiberxavfsizlik Mutaxassisisiz!\n"
                    "Leaderboard sahifasida o'z natijangizni ko'ring.\n"
                    "===================================================================="
                )
            })

        else:
            ctf_num = 1 if active_ctf == 1 else 2
            return jsonify({
                "status": "pass",
                "next_stage": next_stage,
                "message": (
                    "========================================================\n"
                    f"✅ TABRIKLAYMIZ! quiz{stage} muvaffaqiyatli bajarildi (CTF {ctf_num}).\n"
                    f"{score_note}\n"
                    f"🔓 quiz{next_stage} ochildi!\n"
                    f"➡️  O'tish uchun: cd ~/quiz{next_stage}\n"
                    f"📋 Vazifani ko'rish uchun: cat ~/quiz{next_stage}/README.txt\n"
                    "========================================================"
                )
            })

    else:
        db.log_attempt(username, stage, "fail", ctf=active_ctf)
        fail_count = db.get_stage_fail_count(username, stage, ctf=active_ctf)
        hints_dict = HINTS_CTF2 if active_ctf == 2 else HINTS_CTF1
        hints_for_stage = hints_dict.get(stage, {})

        if fail_count <= 3:
            msg = (
                f"❌ Hali to'liq emas yoki xatolik bor! (quiz{stage})\n"
                f"⚠️ Noto'g'ri urinish: {fail_count}/3\n"
                f"💡 Vazifa shartini qayta o'qish uchun: cat ~/quiz{stage}/README.txt\n"
                "🔍 Holatni ko'rish uchun: status"
            )
        elif fail_count == 4:
            hint_text = hints_for_stage.get("hint1", "Vazifa shartiga e'tibor bering.")
            msg = (
                f"❌ Xatolik bor! (Urinish: 4)\n"
                f"{hint_text}\n"
                f"💡 Qayta tekshirish: check"
            )
        elif fail_count == 5:
            hint_text = hints_for_stage.get("hint2", "Parametrlarni ko'rib chiqing.")
            msg = (
                f"❌ Xatolik bor! (Urinish: 5)\n"
                f"{hint_text}\n"
                f"💡 Qayta tekshirish: check"
            )
        elif fail_count == 6:
            hint_text = hints_for_stage.get("hint3", "Buyruqni aniq bajaring.")
            msg = (
                f"❌ Xatolik bor! (Urinish: 6 - So'nggi maslahat)\n"
                f"{hint_text}\n"
                f"💡 Qayta tekshirish: check"
            )
        else:
            msg = (
                f"⚠️ DIQQAT: Siz 6 ta urinish va barcha maslahatlardan foydalandingiz, lekin vazifa hal bo'lmadi! (Urinish: {fail_count})\n"
                f"Ushbu bosqichni to'g'ri bajarmaguningizcha keyingisiga o'tolmaysiz!\n"
                f"📚 Tavsiya: Linux buyruqlari va parametrlari bo'yicha qo'llanmani boshidan qayta o'qib chiqing.\n"
                f"🔍 Holat: status | Yordam: help"
            )

        return jsonify({
            "status": "fail",
            "stage": stage,
            "fail_count": fail_count,
            "message": msg
        })


@app.route("/api/terminal/autocomplete", methods=["POST"])
@login_required
def autocomplete_terminal():
    data = request.json or {}
    text = data.get("text", "")
    cwd = data.get("cwd", "/home/talaba1").replace("\\", "/")
    username = session.get("username", "talaba1")
    fs = get_fs(username)

    def resolve_path(p):
        p = p.replace("\\", "/")
        if p.startswith("~/"):
            p = f"/home/{username}/" + p[2:]
        elif p == "~":
            p = f"/home/{username}"
        elif not p.startswith("/"):
            p = posixpath.join(cwd, p)
        return posixpath.normpath(p)

    cmds = ["ls", "cd", "mkdir", "touch", "nano", "cat", "head", "tail", "rm",
            "chmod", "chown", "check", "status", "reset", "clear", "help", "whoami", "pwd", "sudo", "find", "grep", "wc", "echo", "ctf1", "ctf2", "sort", "uniq"]

    tokens = text.split()
    is_trailing_space = text.endswith(" ")
    matches = []

    if len(tokens) == 0:
        return jsonify({"matches": []})

    if len(tokens) == 1 and not is_trailing_space:
        cmd_prefix = tokens[0]
        matches = [c for c in cmds if c.startswith(cmd_prefix)]
    else:
        last_arg = "" if is_trailing_space else tokens[-1]
        if "/" in last_arg:
            dir_part = posixpath.dirname(last_arg)
            base_prefix = posixpath.basename(last_arg)
            target_dir = resolve_path(dir_part)
            prefix_to_add = dir_part + "/"
        else:
            dir_part = ""
            base_prefix = last_arg
            target_dir = cwd
            prefix_to_add = ""

        if target_dir in fs and fs[target_dir]["type"] == "dir":
            for item in fs[target_dir]["children"]:
                if item.startswith(base_prefix):
                    item_path = posixpath.normpath(posixpath.join(target_dir, item))
                    is_dir = fs.get(item_path, {}).get("type") == "dir"
                    suffix = "/" if is_dir else ""
                    matches.append(prefix_to_add + item + suffix)

    return jsonify({"matches": matches})


# ── Pipeline & Redirection Parsers ──────────────────────────────────────────

def extract_redirection(cmd_str):
    """Extracts output redirection (> or >>) taking into account quotes."""
    in_single = False
    in_double = False
    i = len(cmd_str) - 1
    while i >= 0:
        c = cmd_str[i]
        if c == "'" and not in_double:
            in_single = not in_single
        elif c == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double and c == ">":
            if i > 0 and cmd_str[i - 1] == ">":
                base_cmd = cmd_str[:i - 1].strip()
                target_file = cmd_str[i + 1:].strip()
                return base_cmd, target_file, True
            else:
                base_cmd = cmd_str[:i].strip()
                target_file = cmd_str[i + 1:].strip()
                return base_cmd, target_file, False
        i -= 1
    return cmd_str, None, False


def extract_input_redirection(cmd_str):
    """Extracts input redirection (<) taking into account quotes."""
    in_single = False
    in_double = False
    i = len(cmd_str) - 1
    while i >= 0:
        c = cmd_str[i]
        if c == "'" and not in_double:
            in_single = not in_single
        elif c == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double and c == "<":
            base_cmd = cmd_str[:i].strip()
            source_file = cmd_str[i + 1:].strip()
            return base_cmd, source_file
        i -= 1
    return cmd_str, None


def split_pipeline(cmd_str):
    """Splits command pipeline by | taking into account quotes."""
    parts = []
    current = []
    in_single = False
    in_double = False
    for c in cmd_str:
        if c == "'" and not in_double:
            in_single = not in_single
            current.append(c)
        elif c == '"' and not in_single:
            in_double = not in_double
            current.append(c)
        elif c == "|" and not in_single and not in_double:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(c)
    if current:
        parts.append("".join(current).strip())
    return [p for p in parts if p]


def split_chains(cmd_str):
    """Splits command by && or ; taking into account quotes."""
    chains = []
    current = []
    in_single = False
    in_double = False
    i = 0
    n = len(cmd_str)
    while i < n:
        c = cmd_str[i]
        if c == "'" and not in_double:
            in_single = not in_single
            current.append(c)
            i += 1
        elif c == '"' and not in_single:
            in_double = not in_double
            current.append(c)
            i += 1
        elif not in_single and not in_double:
            if c == "&" and i + 1 < n and cmd_str[i + 1] == "&":
                chains.append("".join(current).strip())
                current = []
                i += 2
            elif c == ";":
                chains.append("".join(current).strip())
                current = []
                i += 1
            else:
                current.append(c)
                i += 1
        else:
            current.append(c)
            i += 1
    if current:
        chains.append("".join(current).strip())
    return [c for c in chains if c]


@app.route("/api/terminal/execute", methods=["POST"])
@login_required
def execute_command():
    data = request.json or {}
    raw_cmd = data.get("command", "").strip()
    cwd = data.get("cwd", "/home/talaba1").replace("\\", "/")
    username = session.get("username", "talaba1")

    if not raw_cmd:
        return jsonify({"output": "", "cwd": cwd})

    fs = get_fs(username)

    def resolve_path(p):
        p = p.replace("\\", "/")
        if p.startswith("~/"):
            p = f"/home/{username}/" + p[2:]
        elif p == "~":
            p = f"/home/{username}"
        elif not p.startswith("/"):
            p = posixpath.join(cwd, p)
        return posixpath.normpath(p)

    def run_single_command(cmd_text, stdin_data=None):
        nonlocal cwd, fs
        parts = cmd_text.split()
        if not parts:
            return ""
        cmd = parts[0]
        args = parts[1:]

        if cmd == "clear":
            return {"action": "clear"}

        elif cmd in ("ctf1", "ctf2"):
            target_ctf = 1 if cmd == "ctf1" else 2
            res = db.switch_active_ctf(username, target_ctf)
            if not res["ok"]:
                return res["error"]
            sync_fs(username)
            cwd = f"/home/{username}"
            label = "CTF 1 (Linux Asoslari)" if target_ctf == 1 else "CTF 2 (Ilg'or Kiberxavfsizlik)"
            return f"🔄 {label} moduliga muvaffaqiyatli o'tildi!\n💡 Boshlash: cd ~/quiz1 && cat README.txt"

        elif cmd == "reset":
            sync_fs(username)
            return "🔄 Joriy bosqich fayllari va tizim yangilandi (tozalandi)!"

        elif cmd == "pwd":
            return cwd

        elif cmd == "whoami":
            return username

        elif cmd == "help":
            return (
                "📌 Mavjud buyruqlar:\n"
                "  ls [-la]                    - papkadagi fayllarni ko'rsatadi\n"
                "  cd <path>                   - katalogga o'tadi\n"
                "  mkdir <dir>                 - papka yaratadi\n"
                "  touch <file>                - fayl hosil qiladi\n"
                "  nano <file>                 - faylni tahrirlash (Web UI editor)\n"
                "  cat [file]                  - fayl ichini o'qiydi (yoki stdin)\n"
                "  head [-n K] [file]          - fayl boshidan K ta qator\n"
                "  tail [-n K] [file]          - fayl oxiridan K ta qator\n"
                "  grep [-w -i -v -n -c] <p>   - matn/fayldan qidiruv\n"
                "  wc [-l -w -c] [file]        - qatorlar (-l), so'zlar (-w), baytlar (-c) sonini sanash\n"
                "  find <dir> [options]        - qidiruv (-name, -size, -perm, -type)\n"
                "  sort [-r -n -u] [file]      - qatorlarni saralash\n"
                "  uniq [-c] [file]            - takroriy qatorlarni tozalash\n"
                "  rm [-r] <path>              - fayl yoki papkani o'chiradi\n"
                "  chmod <mode> <file>         - fayl ruxsatini o'zgartiradi\n"
                "  sudo chown <u> <file>       - fayl egaligini o'zgartiradi\n"
                "  cmd1 | cmd2                 - konveyer (pipe) orqali natijani uzatish\n"
                "  cmd > file (yoki >>)        - natijani faylga yozish/qo'shish\n"
                "  check                       - bosqichni tekshirish\n"
                "  status                      - joriy bosqich ma'lumotlari\n"
                "  reset                       - joriy bosqich fayllarini yangilash / tozalash\n"
                "  ctf1 / ctf2                 - CTF 1 yoki CTF 2 moduliga o'tish\n"
                "  clear                       - ekranni tozalash"
            )

        elif cmd == "status":
            ctf_status = db.get_student_ctf_status(username)
            active_ctf = ctf_status["active_ctf"]
            stage = ctf_status["ctf2_stage"] if active_ctf == 2 else ctf_status["ctf1_stage"]
            ctf_name = "CTF 1: Linux Asoslari" if active_ctf == 1 else "CTF 2: Ilg'or Tizim & Kiberxavfsizlik"
            quiz_dict = QUIZZES_CTF2 if active_ctf == 2 else QUIZZES_CTF1
            quiz_info = quiz_dict.get(stage, {
                "title": "Tugallangan",
                "description": "Barcha 10 ta bosqich muvaffaqiyatli topshirildi!",
                "guide": ""
            })
            fail_cnt = db.get_stage_fail_count(username, stage, ctf=active_ctf)
            stage_str = f"quiz{stage}/10" if stage <= 10 else "Tugallandi! 🏆"
            return (
                f"👤 Foydalanuvchi: {username}\n"
                f"🛡️ Modul: {ctf_name}\n"
                f"🏆 Joriy bosqich: {stage_str}\n"
                f"🎯 Mavzu: {quiz_info.get('title', 'Tugallangan')}\n"
                f"⚠️ Noto'g'ri urinishlar: {fail_cnt}\n"
                f"💡 Tavsif: {quiz_info.get('description', '')}\n"
                f"📋 Ko'rish: {quiz_info.get('guide', '')}"
            )

        elif cmd == "check":
            res = check_quiz()
            res_data = res.get_json()
            return res_data["message"]

        elif cmd == "cd":
            target = args[0] if args else f"/home/{username}"
            resolved = resolve_path(target)
            if resolved in fs and fs[resolved]["type"] == "dir":
                mode = fs[resolved].get("mode", "755")
                has_exec = ("x" in mode or mode in ("755", "777", "775", "111", "555"))
                if not has_exec and mode in ("000", "200", "400", "600", "644"):
                    return f"bash: cd: {target}: Permission denied"
                else:
                    cwd = resolved
                    return ""
            else:
                return f"bash: cd: {target}: No such file or directory"

        elif cmd == "ls":
            show_all = False
            long_format = False
            target_dir = cwd
            for a in args:
                if a.startswith("-"):
                    if "a" in a: show_all = True
                    if "l" in a: long_format = True
                else:
                    target_dir = resolve_path(a)

            if target_dir in fs and fs[target_dir]["type"] == "dir":
                items = fs[target_dir]["children"]
                result_items = []
                for item in items:
                    if not show_all and item.startswith("."):
                        continue
                    item_path = posixpath.normpath(posixpath.join(target_dir, item))
                    item_meta = fs.get(item_path, {})
                    itype = item_meta.get("type", "file")
                    iowner = item_meta.get("owner", username)
                    imode = item_meta.get("mode", "644")
                    if long_format:
                        prefix = "d" if itype == "dir" else "-"
                        if imode == "000": perm = "---------"
                        elif imode in ("200", "-r"): perm = "-w-------"
                        elif imode == "400": perm = "r--------"
                        elif imode in ("600", "rw"): perm = "rw-------"
                        elif imode in ("644", "r", "+r", "u+r"): perm = "rw-r--r--"
                        elif imode in ("755", "x", "+x", "u+x", "+rx", "u+xr", "u+rx"): perm = "rwxr-xr-x"
                        elif imode == "777": perm = "rwxrwxrwx"
                        else: perm = "rwxr-xr-x" if itype == "dir" or "x" in imode else "rw-r--r--"

                        fcontent = item_meta.get("content", "")
                        sz = 4096 if itype == "dir" else len(fcontent.encode("utf-8"))
                        result_items.append(f"{prefix}{perm} 1 {iowner} {iowner} {sz:5d} Sep  9 {item}")
                    else:
                        prefix = "📁 " if itype == "dir" else "📄 "
                        result_items.append(f"{prefix}{item}")
                return "\n".join(result_items) if result_items else ""
            else:
                return f"ls: cannot access '{target_dir}': No such file or directory"

        elif cmd == "mkdir":
            if not args:
                return "mkdir: missing operand"
            msgs = []
            for dirname in args:
                target_path = resolve_path(dirname)
                parent_dir = posixpath.dirname(target_path)
                if parent_dir in fs and fs[parent_dir]["type"] == "dir":
                    base = posixpath.basename(target_path)
                    if base not in fs[parent_dir]["children"]:
                        fs[parent_dir]["children"].append(base)
                    fs[target_path] = {"type": "dir", "owner": username, "mode": "755", "children": []}
                else:
                    msgs.append(f"mkdir: cannot create directory '{dirname}': No such file or directory")
            return "\n".join(msgs)

        elif cmd == "touch":
            if not args:
                return "touch: missing file operand"
            msgs = []
            for fname in args:
                target_path = resolve_path(fname)
                parent_dir = posixpath.dirname(target_path)
                if parent_dir in fs and fs[parent_dir]["type"] == "dir":
                    base = posixpath.basename(target_path)
                    if base not in fs[parent_dir]["children"]:
                        fs[parent_dir]["children"].append(base)
                    if target_path not in fs:
                        fs[target_path] = {"type": "file", "owner": username, "mode": "644", "content": ""}
                else:
                    msgs.append(f"touch: cannot touch '{fname}': No such file or directory")
            return "\n".join(msgs)

        elif cmd == "cat":
            if not args:
                return stdin_data if stdin_data is not None else "cat: missing operand"
            out_parts = []
            for arg_file in args:
                target_path = resolve_path(arg_file)
                if target_path in fs:
                    if fs[target_path]["type"] == "dir":
                        out_parts.append(f"cat: {arg_file}: Is a directory")
                    else:
                        mode = fs[target_path].get("mode", "644")
                        has_read = ("r" in mode or mode in ("644", "755", "777", "444", "666", "700", "600", "400", "775"))
                        if not has_read and mode in ("000", "200", "300", "100", "x"):
                            out_parts.append(f"cat: {arg_file}: Permission denied")
                        else:
                            out_parts.append(fs[target_path]["content"])
                else:
                    hint = ""
                    for k in fs:
                        if posixpath.basename(k) == arg_file and fs[k]["type"] == "file":
                            parent = posixpath.dirname(k).replace(f"/home/{username}", "~")
                            hint = f" (💡 Maslahat: Fayl '{parent}' ichida joylashgan. Avval 'cd {parent}' qiling)"
                            break
                    out_parts.append(f"cat: {arg_file}: No such file or directory{hint}")
            return "\n".join(out_parts)

        elif cmd in ("head", "tail"):
            target_file = None
            count = 10
            idx = 0
            while idx < len(args):
                if args[idx] == "-n" and idx + 1 < len(args):
                    try: count = int(args[idx + 1])
                    except ValueError: pass
                    idx += 2
                elif args[idx].startswith("-") and args[idx][1:].isdigit():
                    count = int(args[idx][1:])
                    idx += 1
                else:
                    target_file = args[idx]
                    idx += 1

            lines = []
            if target_file:
                target_path = resolve_path(target_file)
                if target_path in fs and fs[target_path]["type"] == "file":
                    lines = fs[target_path]["content"].splitlines()
                elif target_path in fs and fs[target_path]["type"] == "dir":
                    return f"{cmd}: error reading '{target_file}': Is a directory"
                else:
                    return f"{cmd}: {target_file}: No such file or directory"
            elif stdin_data is not None:
                lines = stdin_data.splitlines()
            else:
                return f"{cmd}: missing file operand"

            if cmd == "head":
                return "\n".join(lines[:count])
            else:
                return "\n".join(lines[-count:] if count > 0 else [])

        elif cmd == "grep":
            word_match = False
            ignore_case = False
            invert_match = False
            line_numbers = False
            count_only = False
            non_flag_args = []

            for a in args:
                if a.startswith("-") and len(a) > 1 and not a.startswith("--"):
                    if "w" in a: word_match = True
                    if "i" in a: ignore_case = True
                    if "v" in a: invert_match = True
                    if "n" in a: line_numbers = True
                    if "c" in a: count_only = True
                elif a == "--word-regexp": word_match = True
                elif a == "--ignore-case": ignore_case = True
                elif a == "--invert-match": invert_match = True
                elif a == "--line-number": line_numbers = True
                elif a == "--count": count_only = True
                else:
                    non_flag_args.append(a)

            if not non_flag_args:
                return "grep: missing pattern"

            pattern = non_flag_args[0].strip("'\"")
            lines_to_search = []

            if len(non_flag_args) >= 2:
                target_file = non_flag_args[-1]
                target_path = resolve_path(target_file)
                if target_path in fs and fs[target_path]["type"] == "file":
                    lines_to_search = fs[target_path]["content"].splitlines()
                elif target_path in fs and fs[target_path]["type"] == "dir":
                    return f"grep: {target_file}: Is a directory"
                else:
                    hint = ""
                    for k in fs:
                        if posixpath.basename(k) == target_file and fs[k]["type"] == "file":
                            parent = posixpath.dirname(k).replace(f"/home/{username}", "~")
                            hint = f" (💡 Maslahat: Fayl '{parent}' ichida joylashgan. Avval 'cd {parent}' qiling)"
                            break
                    return f"grep: {target_file}: No such file or directory{hint}"
            elif stdin_data is not None:
                lines_to_search = stdin_data.splitlines()
            else:
                return "grep: missing file operand"

            import re
            matched = []
            flags = re.IGNORECASE if ignore_case else 0
            regex_pat = r'\b' + re.escape(pattern) + r'\b' if word_match else re.escape(pattern)

            for idx_l, line in enumerate(lines_to_search, 1):
                has_match = bool(re.search(regex_pat, line, flags))
                if invert_match:
                    has_match = not has_match
                if has_match:
                    if line_numbers:
                        matched.append(f"{idx_l}:{line}")
                    else:
                        matched.append(line)

            if count_only:
                return str(len(matched))
            return "\n".join(matched) if matched else ""

        elif cmd == "wc":
            lines_flag = False
            words_flag = False
            bytes_flag = False
            chars_flag = False
            max_line_flag = False
            target_files = []

            for a in args:
                if a.startswith("--"):
                    if a == "--lines": lines_flag = True
                    elif a == "--words": words_flag = True
                    elif a == "--bytes": bytes_flag = True
                    elif a == "--chars": chars_flag = True
                    elif a == "--max-line-length": max_line_flag = True
                elif a.startswith("-") and len(a) > 1:
                    if "l" in a: lines_flag = True
                    if "w" in a: words_flag = True
                    if "c" in a: bytes_flag = True
                    if "m" in a: chars_flag = True
                    if "L" in a: max_line_flag = True
                else:
                    target_files.append(a)

            default_all = not (lines_flag or words_flag or bytes_flag or chars_flag or max_line_flag)

            def calc_wc_stats(text):
                if not text:
                    l_cnt = 0
                    w_cnt = 0
                    b_cnt = 0
                    c_cnt = 0
                    max_l = 0
                else:
                    lines = text.splitlines()
                    l_cnt = len(lines)
                    w_cnt = len(text.split())
                    b_cnt = len(text.encode("utf-8"))
                    c_cnt = len(text)
                    max_l = max([len(l) for l in lines]) if lines else 0

                res_p = []
                if lines_flag or default_all: res_p.append(str(l_cnt))
                if words_flag or default_all: res_p.append(str(w_cnt))
                if bytes_flag or default_all: res_p.append(str(b_cnt))
                if chars_flag: res_p.append(str(c_cnt))
                if max_line_flag: res_p.append(str(max_l))
                return res_p

            # Case A: Piped data into wc (e.g. cat file | wc -l or wc -l < file)
            if stdin_data is not None and not target_files:
                stats = calc_wc_stats(stdin_data)
                return " ".join(stats)

            # Case B: No files and no stdin
            if not target_files:
                return "wc: standart kiritish (stdin) bo'sh. Foydalanish: 'wc -l <fayl>' yoki 'cat <fayl> | wc -l'"

            # Case C: File arguments
            expanded = []
            for tf in target_files:
                if tf == "*":
                    for k, meta in fs.items():
                        if posixpath.dirname(k) == cwd and meta.get("type") == "file":
                            expanded.append(posixpath.basename(k))
                else:
                    expanded.append(tf)

            out_lines = []
            tot_l, tot_w, tot_b = 0, 0, 0
            for tf in expanded:
                target_path = resolve_path(tf)
                if target_path in fs and fs[target_path]["type"] == "file":
                    cnt = fs[target_path]["content"]
                    stats = calc_wc_stats(cnt)
                    stats.append(tf)
                    out_lines.append(" ".join(stats))
                    tot_l += len(cnt.splitlines()) if cnt else 0
                    tot_w += len(cnt.split()) if cnt else 0
                    tot_b += len(cnt.encode("utf-8")) if cnt else 0
                elif target_path in fs and fs[target_path]["type"] == "dir":
                    out_lines.append(f"wc: {tf}: Is a directory")
                else:
                    hint = ""
                    for k in fs:
                        if posixpath.basename(k) == tf and fs[k]["type"] == "file":
                            parent = posixpath.dirname(k).replace(f"/home/{username}", "~")
                            hint = f" (💡 Maslahat: Fayl '{parent}' ichida. Avval 'cd {parent}' qiling)"
                            break
                    out_lines.append(f"wc: {tf}: No such file or directory{hint}")

            if len(expanded) > 1:
                tot_p = []
                if lines_flag or default_all: tot_p.append(str(tot_l))
                if words_flag or default_all: tot_p.append(str(tot_w))
                if bytes_flag or default_all: tot_p.append(str(tot_b))
                tot_p.append("total")
                out_lines.append(" ".join(tot_p))
            return "\n".join(out_lines)

        elif cmd == "sort":
            reverse = "-r" in args
            numeric = "-n" in args
            unique = "-u" in args
            files = [a for a in args if not a.startswith("-")]

            lines = []
            if files:
                target_path = resolve_path(files[0])
                if target_path in fs and fs[target_path]["type"] == "file":
                    lines = fs[target_path]["content"].splitlines()
                else:
                    return f"sort: {files[0]}: No such file or directory"
            elif stdin_data is not None:
                lines = stdin_data.splitlines()
            else:
                return ""

            if numeric:
                def num_key(val):
                    try: return float(val.split()[0])
                    except Exception: return 0
                lines = sorted(lines, key=num_key, reverse=reverse)
            else:
                lines = sorted(lines, reverse=reverse)

            if unique:
                seen = set()
                dedup = []
                for l in lines:
                    if l not in seen:
                        seen.add(l)
                        dedup.append(l)
                lines = dedup
            return "\n".join(lines)

        elif cmd == "uniq":
            count_flag = "-c" in args
            files = [a for a in args if not a.startswith("-")]
            lines = []
            if files:
                target_path = resolve_path(files[0])
                if target_path in fs and fs[target_path]["type"] == "file":
                    lines = fs[target_path]["content"].splitlines()
                else:
                    return f"uniq: {files[0]}: No such file or directory"
            elif stdin_data is not None:
                lines = stdin_data.splitlines()
            else:
                return ""

            result = []
            prev = None
            cnt = 0
            for l in lines:
                if l == prev:
                    cnt += 1
                else:
                    if prev is not None:
                        if count_flag: result.append(f"{cnt:4d} {prev}")
                        else: result.append(prev)
                    prev = l
                    cnt = 1
            if prev is not None:
                if count_flag: result.append(f"{cnt:4d} {prev}")
                else: result.append(prev)
            return "\n".join(result)

        elif cmd == "find":
            search_dir = cwd
            name_pattern = None
            size_filter = None
            perm_filter = None
            type_filter = None
            empty_filter = False

            idx = 0
            while idx < len(args):
                arg = args[idx]
                if arg == "-name" and idx + 1 < len(args):
                    name_pattern = args[idx + 1].strip("'\"*")
                    idx += 2
                elif arg == "-size" and idx + 1 < len(args):
                    size_filter = args[idx + 1].strip()
                    idx += 2
                elif arg == "-perm" and idx + 1 < len(args):
                    perm_filter = args[idx + 1].strip()
                    idx += 2
                elif arg == "-type" and idx + 1 < len(args):
                    type_filter = args[idx + 1].strip()
                    idx += 2
                elif arg == "-empty":
                    empty_filter = True
                    idx += 1
                elif not arg.startswith("-"):
                    search_dir = resolve_path(arg)
                    idx += 1
                else:
                    idx += 1

            results = []
            for path_key, item_meta in fs.items():
                if path_key == search_dir:
                    continue
                if path_key.startswith(search_dir + "/") or (search_dir == "/" and path_key.startswith("/")):
                    basename = posixpath.basename(path_key)
                    itype = item_meta.get("type", "file")
                    imode = item_meta.get("mode", "644")
                    content = item_meta.get("content", "")
                    byte_size = len(content.encode("utf-8")) if itype == "file" else 4096

                    if name_pattern and name_pattern not in basename:
                        continue
                    if type_filter:
                        if type_filter == "f" and itype != "file": continue
                        if type_filter == "d" and itype != "dir": continue
                    if perm_filter:
                        if perm_filter not in imode: continue
                    if empty_filter:
                        if itype == "file" and len(content) > 0: continue
                    if size_filter:
                        sz_str = size_filter.strip().lower()
                        mode_sign = None
                        if sz_str.startswith("+"): mode_sign = "+"; sz_str = sz_str[1:]
                        elif sz_str.startswith("-"): mode_sign = "-"; sz_str = sz_str[1:]

                        multiplier = 1
                        if sz_str.endswith("c"): multiplier = 1; num_part = sz_str[:-1]
                        elif sz_str.endswith("k"): multiplier = 1024; num_part = sz_str[:-1]
                        elif sz_str.endswith("m"): multiplier = 1024 * 1024; num_part = sz_str[:-1]
                        elif sz_str.endswith("b"): multiplier = 1; num_part = sz_str[:-1]
                        else: num_part = sz_str

                        try:
                            target_bytes = int(num_part) * multiplier
                            if mode_sign == "+" and byte_size <= target_bytes: continue
                            elif mode_sign == "-" and byte_size >= target_bytes: continue
                            elif mode_sign is None and byte_size != target_bytes: continue
                        except ValueError:
                            pass

                    rel = path_key.replace(f"/home/{username}", "~")
                    results.append(rel)
            return "\n".join(sorted(results)) if results else ""

        elif cmd == "rm":
            recursive = False
            files_to_remove = []
            for a in args:
                if a in ["-r", "-rf", "-f", "-fr"] or (a.startswith("-") and "r" in a):
                    recursive = True
                else:
                    files_to_remove.append(a)

            msgs = []
            for fname in files_to_remove:
                target_path = resolve_path(fname)
                if target_path in fs:
                    if fs[target_path]["type"] == "dir" and not recursive:
                        msgs.append(f"rm: cannot remove '{fname}': Is a directory")
                    else:
                        keys_to_del = [k for k in fs if k == target_path or k.startswith(target_path + "/")]
                        for k in keys_to_del:
                            del fs[k]
                        parent_dir = posixpath.dirname(target_path)
                        base = posixpath.basename(target_path)
                        if parent_dir in fs and base in fs[parent_dir]["children"]:
                            fs[parent_dir]["children"].remove(base)
                else:
                    msgs.append(f"rm: cannot remove '{fname}': No such file or directory")
            return "\n".join(msgs)

        elif cmd == "chmod":
            if len(args) < 2:
                return "chmod: usage: chmod <mode> <file>"
            mode_arg = args[0]
            target_file = args[1]
            target_path = resolve_path(target_file)
            if target_path in fs:
                if "+x" in mode_arg or "+rx" in mode_arg or "+xr" in mode_arg or "u+xr" in mode_arg or "u+rx" in mode_arg or "755" in mode_arg or "777" in mode_arg or mode_arg in ("x", "+x", "u+x"):
                    fs[target_path]["mode"] = "755"
                elif "+r" in mode_arg or "644" in mode_arg or mode_arg in ("r", "+r", "u+r", "444"):
                    fs[target_path]["mode"] = "644"
                elif "-r" in mode_arg or "200" in mode_arg:
                    fs[target_path]["mode"] = "200"
                elif "000" in mode_arg:
                    fs[target_path]["mode"] = "000"
                else:
                    fs[target_path]["mode"] = mode_arg
                return ""
            else:
                return f"chmod: cannot access '{target_file}': No such file or directory"

        elif cmd == "sudo":
            if len(args) >= 3 and args[0] == "chown":
                user_target = args[1]
                file_target = args[2]
                target_path = resolve_path(file_target)
                if target_path in fs:
                    fs[target_path]["owner"] = user_target
                    return ""
                else:
                    return f"chown: cannot access '{file_target}': No such file or directory"
            else:
                return f"sudo: {' '.join(args)}: command not found"

        elif cmd == "chown":
            if len(args) >= 2:
                user_target = args[0]
                file_target = args[1]
                target_path = resolve_path(file_target)
                if target_path in fs:
                    fs[target_path]["owner"] = user_target
                    return ""
                else:
                    return f"chown: cannot access '{file_target}': No such file or directory"
            else:
                return "chown: usage: chown <user> <file>"

        elif cmd.startswith("./"):
            script_name = cmd[2:]
            target_path = resolve_path(script_name)
            if target_path in fs:
                mode = fs[target_path].get("mode", "644")
                is_exec = ("x" in mode or mode in ("755", "777", "111", "775"))
                if is_exec:
                    script_content = fs[target_path]["content"]
                    script_dir = posixpath.dirname(target_path)
                    if "done.txt" in script_content:
                        created_file = posixpath.join(script_dir, "done.txt")
                        fs[created_file] = {"type": "file", "owner": username, "mode": "644", "content": "muvaffaqiyatli"}
                        if "done.txt" not in fs[script_dir]["children"]:
                            fs[script_dir]["children"].append("done.txt")
                        return "Skript ishga tushdi!"
                    elif "result.txt" in script_content:
                        created_file = posixpath.join(script_dir, "result.txt")
                        fs[created_file] = {"type": "file", "owner": username, "mode": "644", "content": "Tabriklaymiz, siz oxirgi bosqichga yetdingiz!"}
                        if "result.txt" not in fs[script_dir]["children"]:
                            fs[script_dir]["children"].append("result.txt")
                        return "SUCCESS: result.txt created!"
                    else:
                        return "Execution finished."
                else:
                    return f"bash: ./{script_name}: Permission denied"
            else:
                return f"bash: ./{script_name}: No such file or directory"

        elif cmd == "nano":
            if not args:
                return "nano: missing file operand"
            target_path = resolve_path(args[0])
            content = ""
            if target_path in fs and fs[target_path]["type"] == "file":
                content = fs[target_path]["content"]
            return {
                "action": "open_editor",
                "path": target_path,
                "filename": posixpath.basename(target_path),
                "content": content,
                "cwd": cwd
            }

        elif cmd == "echo":
            text = cmd_text.replace("echo", "", 1).strip()
            if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
                text = text[1:-1]
            return text

        else:
            return f"bash: {cmd}: command not found"

    # ── Command Execution (Chaining &&/;, Pipelines |, Redirection >/<) ──
    chains = split_chains(raw_cmd)
    chain_outputs = []

    for one_chain in chains:
        # 1. Output redirection (> or >>)
        cmd_body, redirect_target, redirect_append = extract_redirection(one_chain)

        # 2. Input redirection (<)
        cmd_body, in_file = extract_input_redirection(cmd_body)
        stdin_data = None
        if in_file:
            in_path = resolve_path(in_file)
            if in_path in fs and fs[in_path]["type"] == "file":
                stdin_data = fs[in_path]["content"]
            else:
                return jsonify({"output": f"bash: {in_file}: No such file or directory", "cwd": cwd})

        # 3. Pipeline execution (|)
        pipeline_stages = split_pipeline(cmd_body)
        curr_input = stdin_data

        for stage_cmd in pipeline_stages:
            if not stage_cmd:
                continue
            stage_res = run_single_command(stage_cmd, stdin_data=curr_input)
            if isinstance(stage_res, dict):
                if stage_res.get("action") == "clear":
                    return jsonify({"output": "__CLEAR__", "cwd": cwd})
                if stage_res.get("action") == "open_editor":
                    return jsonify(stage_res)
            curr_input = str(stage_res)

        part_out = curr_input if curr_input is not None else ""

        # 4. Save output redirection to VFS
        if redirect_target:
            target_path = resolve_path(redirect_target)
            parent_dir = posixpath.dirname(target_path)
            if parent_dir in fs and fs[parent_dir]["type"] == "dir":
                base = posixpath.basename(target_path)
                if base not in fs[parent_dir]["children"]:
                    fs[parent_dir]["children"].append(base)

                if redirect_append and target_path in fs:
                    prev_c = fs[target_path]["content"]
                    fs[target_path]["content"] = prev_c + ("\n" if prev_c and not prev_c.endswith("\n") else "") + part_out
                else:
                    fs[target_path] = {"type": "file", "owner": username, "mode": "644", "content": part_out}
                part_out = ""
            else:
                part_out = f"bash: {redirect_target}: No such file or directory"

        if part_out:
            chain_outputs.append(part_out)

    final_output = "\n".join(chain_outputs)
    db.save_user_vfs(username, fs)
    return jsonify({"output": final_output, "cwd": cwd})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
