import os
import hashlib
import json
import string
import random
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import database as db

app = Flask(__name__)
app.secret_key = "ctf_secret_key_linux_web_2026"
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

# Quiz metadata (for status command only)
QUIZZES = {
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
        "title": "quiz10: Yakuniy buyruq va Flag olish",
        "commands": "chmod, ./final.sh, check",
        "description": "~/quiz10/final.sh skriptini bajariladigan qiling va ishga tushiring, so'ng terminalda 'check' deb yozing!",
        "guide": "cat ~/quiz10/README.txt"
    }
}


def generate_key(prefix, length=8):
    chars = string.ascii_uppercase + string.digits
    return prefix + ''.join(random.choices(chars, k=length))


def get_user_fs(username):
    db.seed_student(username)
    answers = db.get_student_answers(username)
    stage = db.get_student_stage(username)

    fs = {
        "/": {"type": "dir", "owner": "root", "mode": "755", "children": ["home", "var", "bin", "tmp", "etc"]},
        "/home": {"type": "dir", "owner": "root", "mode": "755", "children": [username]},
        f"/home/{username}": {
            "type": "dir", "owner": username, "mode": "700",
            "children": ["ROADMAP.txt"] + [f"quiz{i}" for i in range(1, min(stage + 1, 11))]
        },
        f"/home/{username}/ROADMAP.txt": {
            "type": "file", "owner": username, "mode": "644",
            "content": (
                "========================================================================\n"
                "🚩 LINUX CTF ROADMAP (YO'L XARITASI) 🚩\n"
                "========================================================================\n\n"
                "📌 ASOSIY BUYRUQLAR:\n"
                "  • check   - Joriy bosqichdagi vazifangiz to'g'ri bajarilganini tekshiradi.\n"
                "  • status  - Hozir qaysi bosqichda ekanligingiz va vazifa shartini ko'rsatadi.\n\n"
                "🗺 BOSQICHLAR XARITASI (10 TA BOSQICH):\n"
                "  1. quiz1  | mkdir, cd, ls       | images, docs, documents papkalarini yaratish\n"
                "  2. quiz2  | touch, cd            | docs/ ichida notes.txt va todo.txt yaratish\n"
                "  3. quiz3  | nano, cat, echo      | notes.txt ichiga \"linux200\" yozish\n"
                "  4. quiz4  | head, tail, grep     | bigfile.log dan KEY-... ni topib answer.txt ga yozish\n"
                "  5. quiz5  | less, more, grep     | bigfile2.txt dan PASS-... ni topib answer.txt ga yozish\n"
                "  6. quiz6  | rm, rm -r            | Keraksiz fayl va papkalarni xavfsiz o'chirish\n"
                "  7. quiz7  | chmod, ./            | script.sh ga execute ruxsati berish va ishga tushirish\n"
                "  8. quiz8  | chown, sudo          | secret.txt faylini o'zingizga biriktirish\n"
                "  9. quiz9  | ls -la, cd, cat      | Yashirin .flag_part faylini topish va saqlash\n"
                " 10. quiz10 | Final Bosqich        | final.sh ni ishga tushirish va FLAG ni qo'lga kiritish!\n\n"
                "🚀 Boshlash uchun:\n"
                "  cd ~/quiz1\n"
                "  cat README.txt\n\n"
                "Omad tilaymiz!\n"
                "========================================================================"
            )
        }
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

    return fs


USER_FILESYSTEMS = {}


def get_fs(username):
    if username not in USER_FILESYSTEMS:
        USER_FILESYSTEMS[username] = get_user_fs(username)
    return USER_FILESYSTEMS[username]


def sync_fs(username):
    USER_FILESYSTEMS[username] = get_user_fs(username)
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
    stage = db.get_student_stage(username)
    return render_template("index.html", username=username, stage=stage)


@app.route("/api/status", methods=["GET"])
@login_required
def get_status():
    username = session.get("username", "talaba1")
    stage = db.get_student_stage(username)
    quiz_info = QUIZZES.get(stage, {"title": "Tugallangan", "description": "Barcha 10 ta bosqich muvaffaqiyatli topshirildi!"})
    return jsonify({
        "username": username,
        "current_stage": stage,
        "quiz": quiz_info,
        "completed": stage > 10
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


@app.route("/api/file/read", methods=["POST"])
@login_required
def read_file():
    data = request.json or {}
    path = data.get("path", "")
    username = session.get("username", "talaba1")
    fs = get_fs(username)
    if path in fs and fs[path]["type"] == "file":
        return jsonify({"status": "ok", "content": fs[path]["content"]})
    return jsonify({"status": "error", "message": f"Fayl topilmadi: {path}"}), 404


@app.route("/api/file/write", methods=["POST"])
@login_required
def save_file():
    data = request.json or {}
    path = data.get("path", "")
    content = data.get("content", "")
    username = session.get("username", "talaba1")
    fs = get_fs(username)

    parent_dir = os.path.dirname(path)
    if parent_dir not in fs or fs[parent_dir]["type"] != "dir":
        return jsonify({"status": "error", "message": f"Papka mavjud emas: {parent_dir}"}), 400

    filename = os.path.basename(path)
    if filename not in fs[parent_dir]["children"]:
        fs[parent_dir]["children"].append(filename)

    fs[path] = {"type": "file", "owner": username, "mode": "644", "content": content}
    return jsonify({"status": "ok", "message": f"Fayl saqlandi: {path}"})


@app.route("/api/check", methods=["POST"])
@login_required
def check_quiz():
    username = session.get("username", "talaba1")
    stage = db.get_student_stage(username)
    fs = get_fs(username)

    if stage > 10:
        flag = db.get_leaderboard()
        return jsonify({
            "status": "pass",
            "stage": stage,
            "message": "🎉 Siz barcha bosqichlarni tugatgansiz! Leaderboard'dan flagingizni ko'ring."
        })

    passed = False

    # quiz1: images, docs, documents papkalari mavjudligi
    if stage == 1:
        d1 = f"/home/{username}/quiz1/images"
        d2 = f"/home/{username}/quiz1/docs"
        d3 = f"/home/{username}/quiz1/documents"
        if (d1 in fs and fs[d1]["type"] == "dir" and
                d2 in fs and fs[d2]["type"] == "dir" and
                d3 in fs and fs[d3]["type"] == "dir"):
            passed = True

    # quiz2: docs/notes.txt va docs/todo.txt mavjudligi
    elif stage == 2:
        f1 = f"/home/{username}/quiz2/docs/notes.txt"
        f2 = f"/home/{username}/quiz2/docs/todo.txt"
        if (f1 in fs and fs[f1]["type"] == "file" and
                f2 in fs and fs[f2]["type"] == "file"):
            passed = True

    # quiz3: notes.txt ichida "linux200" bor
    elif stage == 3:
        f = f"/home/{username}/quiz3/notes.txt"
        if f in fs and fs[f]["type"] == "file" and "linux200" in fs[f]["content"]:
            passed = True

    # quiz4: answer.txt ichida KEY-... qiymati to'g'ri
    elif stage == 4:
        f = f"/home/{username}/quiz4/answer.txt"
        expected = db.get_student_answers(username).get(4, "")
        if f in fs and fs[f]["type"] == "file":
            given = fs[f]["content"].strip().replace(" ", "").replace("\n", "")
            if given == expected:
                passed = True

    # quiz5: answer.txt ichida PASS-... qiymati to'g'ri
    elif stage == 5:
        f = f"/home/{username}/quiz5/answer.txt"
        expected = db.get_student_answers(username).get(5, "")
        if f in fs and fs[f]["type"] == "file":
            given = fs[f]["content"].strip().replace(" ", "").replace("\n", "")
            if given == expected:
                passed = True

    # quiz6: temp1, temp2, junk o'chirilgan; required.txt saqlanib qolgan
    elif stage == 6:
        req = f"/home/{username}/quiz6/required.txt"
        t1 = f"/home/{username}/quiz6/temp1.txt"
        t2 = f"/home/{username}/quiz6/temp2.txt"
        junk = f"/home/{username}/quiz6/junk"
        if req in fs and t1 not in fs and t2 not in fs and junk not in fs:
            passed = True

    # quiz7: script.sh executable va done.txt mavjud
    elif stage == 7:
        s = f"/home/{username}/quiz7/script.sh"
        d = f"/home/{username}/quiz7/done.txt"
        mode = fs.get(s, {}).get("mode", "644")
        is_exec = ("x" in mode or mode in ("755", "777", "775", "111"))
        if s in fs and is_exec and d in fs and fs[d]["type"] == "file":
            passed = True

    # quiz8: secret.txt egasi talaba username ga o'zgargan
    elif stage == 8:
        sec = f"/home/{username}/quiz8/secret.txt"
        if sec in fs and fs[sec]["owner"] == username:
            passed = True

    # quiz9: answer.txt ichida PART-... qiymati to'g'ri
    elif stage == 9:
        f = f"/home/{username}/quiz9/answer.txt"
        expected = db.get_student_answers(username).get(9, "")
        if f in fs and fs[f]["type"] == "file":
            given = fs[f]["content"].strip().replace(" ", "").replace("\n", "")
            if given == expected:
                passed = True

    # quiz10: final.sh executable va result.txt mavjud
    elif stage == 10:
        fin = f"/home/{username}/quiz10/final.sh"
        res = f"/home/{username}/quiz10/result.txt"
        mode = fs.get(fin, {}).get("mode", "644")
        is_exec = ("x" in mode or mode in ("755", "777", "775", "111"))
        if fin in fs and is_exec and res in fs and fs[res]["type"] == "file":
            passed = True

    if passed:
        db.log_attempt(username, stage, "pass")
        next_stage = stage + 1
        db.update_student_stage(username, next_stage)
        sync_fs(username)

        if next_stage > 10:
            secret = "CTF_SECRET_KEY_2026"
            flag_hash = hashlib.sha256(f"{username}{secret}".encode()).hexdigest()[:20]
            flag = f"CTF{{{flag_hash}}}"
            db.save_student_flag(username, flag)
            return jsonify({
                "status": "completed",
                "next_stage": 11,
                "message": (
                    "========================================================\n"
                    "🎉🎉🎉 TABRIKLAYMIZ! SIZ CTF'NI TO'LIQ TUGATDINGIZ! 🎉🎉🎉\n"
                    "Sizning shaxsiy flag'ingiz:\n\n"
                    f"    {flag}\n\n"
                    "Ushbu flagni o'qituvchingizga topshiring.\n"
                    "========================================================"
                )
            })
        else:
            return jsonify({
                "status": "pass",
                "next_stage": next_stage,
                "message": (
                    "========================================================\n"
                    f"✅ TABRIKLAYMIZ! quiz{stage} muvaffaqiyatli bajarildi.\n"
                    f"🔓 quiz{next_stage} ochildi!\n"
                    f"➡️  O'tish uchun: cd ~/quiz{next_stage}\n"
                    f"📋 Vazifani ko'rish uchun: cat ~/quiz{next_stage}/README.txt\n"
                    "========================================================"
                )
            })
    else:
        db.log_attempt(username, stage, "fail")
        return jsonify({
            "status": "fail",
            "stage": stage,
            "message": (
                f"❌ Hali to'liq emas yoki xatolik bor! (quiz{stage})\n"
                f"💡 Vazifa shartini qayta o'qish uchun: cat ~/quiz{stage}/README.txt\n"
                "🔍 Holatni ko'rish uchun: status"
            )
        })


@app.route("/api/terminal/autocomplete", methods=["POST"])
@login_required
def autocomplete_terminal():
    data = request.json or {}
    text = data.get("text", "")
    cwd = data.get("cwd", "/home/talaba1")
    username = session.get("username", "talaba1")
    fs = get_fs(username)

    def resolve_path(p):
        if p.startswith("~/"):
            p = f"/home/{username}/" + p[2:]
        elif p == "~":
            p = f"/home/{username}"
        elif not p.startswith("/"):
            p = os.path.normpath(os.path.join(cwd, p))
        return os.path.normpath(p)

    cmds = ["ls", "cd", "mkdir", "touch", "nano", "cat", "head", "tail", "rm",
            "chmod", "chown", "check", "status", "clear", "help", "whoami", "pwd", "sudo", "find", "grep", "echo"]

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
            dir_part = os.path.dirname(last_arg)
            base_prefix = os.path.basename(last_arg)
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
                    item_path = os.path.normpath(os.path.join(target_dir, item))
                    is_dir = fs.get(item_path, {}).get("type") == "dir"
                    suffix = "/" if is_dir else ""
                    matches.append(prefix_to_add + item + suffix)

    return jsonify({"matches": matches})


@app.route("/api/terminal/execute", methods=["POST"])
@login_required
def execute_command():
    data = request.json or {}
    raw_cmd = data.get("command", "").strip()
    cwd = data.get("cwd", "/home/talaba1")
    username = session.get("username", "talaba1")

    if not raw_cmd:
        return jsonify({"output": "", "cwd": cwd})

    fs = get_fs(username)
    stage = db.get_student_stage(username)

    def resolve_path(p):
        if p.startswith("~/"):
            p = f"/home/{username}/" + p[2:]
        elif p == "~":
            p = f"/home/{username}"
        elif not p.startswith("/"):
            p = os.path.normpath(os.path.join(cwd, p))
        return os.path.normpath(p)

    output = ""
    parts = raw_cmd.split()
    cmd = parts[0]
    args = parts[1:]

    if cmd == "clear":
        return jsonify({"output": "__CLEAR__", "cwd": cwd})

    elif cmd == "pwd":
        output = cwd

    elif cmd == "whoami":
        output = username

    elif cmd == "help":
        output = (
            "📌 Mavjud buyruqlar:\n"
            "  ls [-la]              - papkadagi fayllarni ko'rsatadi\n"
            "  cd <path>             - katalogga o'tadi\n"
            "  mkdir <dir>           - papka yaratadi\n"
            "  touch <file>          - fayl hosil qiladi\n"
            "  nano <file>           - faylni tahrirlash (Web UI editor)\n"
            "  cat <file>            - fayl ichini o'qiydi\n"
            "  head [-n K] <file>    - fayl boshidan K ta qator\n"
            "  tail [-n K] <file>    - fayl oxiridan K ta qator\n"
            "  grep <pattern> <file> - fayldan matn qidiradi\n"
            "  find <dir> -name <p>  - fayl qidiradi\n"
            "  rm [-r] <path>        - fayl yoki papkani o'chiradi\n"
            "  chmod <+x> <file>     - fayl ruxsatini o'zgartiradi\n"
            "  sudo chown <u> <file> - fayl egaligini o'zgartiradi\n"
            "  echo <text> > <file>  - faylga matn yozadi\n"
            "  check                 - bosqichni tekshirish\n"
            "  status                - joriy bosqich ma'lumotlari\n"
            "  clear                 - ekranni tozalash"
        )

    elif cmd == "status":
        quiz_info = QUIZZES.get(stage, {})
        output = (
            f"👤 Foydalanuvchi: {username}\n"
            f"🏆 Joriy bosqich: quiz{stage}\n"
            f"🎯 Mavzu: {quiz_info.get('title', 'Tugallangan')}\n"
            f"💡 Tavsif: {quiz_info.get('description', '')}\n"
            f"📋 Ko'rish: {quiz_info.get('guide', '')}"
        )

    elif cmd == "check":
        res = check_quiz()
        res_data = res.get_json()
        output = res_data["message"]

    elif cmd == "cd":
        target = args[0] if args else f"/home/{username}"
        resolved = resolve_path(target)
        if resolved in fs and fs[resolved]["type"] == "dir":
            cwd = resolved
            output = ""
        else:
            output = f"bash: cd: {target}: No such file or directory"

    elif cmd == "ls":
        show_all = False
        long_format = False
        target_dir = cwd
        for a in args:
            if a.startswith("-"):
                if "a" in a:
                    show_all = True
                if "l" in a:
                    long_format = True
            else:
                target_dir = resolve_path(a)

        if target_dir in fs and fs[target_dir]["type"] == "dir":
            items = fs[target_dir]["children"]
            result_items = []
            for item in items:
                if not show_all and item.startswith("."):
                    continue
                item_path = os.path.normpath(os.path.join(target_dir, item))
                item_meta = fs.get(item_path, {})
                itype = item_meta.get("type", "file")
                iowner = item_meta.get("owner", username)
                imode = item_meta.get("mode", "644")
                if long_format:
                    prefix = "d" if itype == "dir" else "-"
                    perm = "rwxr-xr-x" if itype == "dir" or "x" in imode else "rw-r--r--"
                    result_items.append(f"{prefix}{perm} 1 {iowner} {iowner} 4096 Sep  9 {item}")
                else:
                    prefix = "📁 " if itype == "dir" else "📄 "
                    result_items.append(f"{prefix}{item}")
            output = "\n".join(result_items) if result_items else ""
        else:
            output = f"ls: cannot access '{target_dir}': No such file or directory"

    elif cmd == "mkdir":
        if not args:
            output = "mkdir: missing operand"
        else:
            msgs = []
            for dirname in args:
                target_path = resolve_path(dirname)
                parent_dir = os.path.dirname(target_path)
                if parent_dir in fs and fs[parent_dir]["type"] == "dir":
                    base = os.path.basename(target_path)
                    if base not in fs[parent_dir]["children"]:
                        fs[parent_dir]["children"].append(base)
                    fs[target_path] = {"type": "dir", "owner": username, "mode": "755", "children": []}
                else:
                    msgs.append(f"mkdir: cannot create directory '{dirname}': No such file or directory")
            output = "\n".join(msgs)

    elif cmd == "touch":
        if not args:
            output = "touch: missing file operand"
        else:
            msgs = []
            for fname in args:
                target_path = resolve_path(fname)
                parent_dir = os.path.dirname(target_path)
                if parent_dir in fs and fs[parent_dir]["type"] == "dir":
                    base = os.path.basename(target_path)
                    if base not in fs[parent_dir]["children"]:
                        fs[parent_dir]["children"].append(base)
                    if target_path not in fs:
                        fs[target_path] = {"type": "file", "owner": username, "mode": "644", "content": ""}
                else:
                    msgs.append(f"touch: cannot touch '{fname}': No such file or directory")
            output = "\n".join(msgs)

    elif cmd == "cat":
        if not args:
            output = "cat: missing operand"
        else:
            target_path = resolve_path(args[0])
            if target_path in fs:
                if fs[target_path]["type"] == "dir":
                    output = f"cat: {args[0]}: Is a directory"
                else:
                    output = fs[target_path]["content"]
            else:
                output = f"cat: {args[0]}: No such file or directory"

    elif cmd in ("head", "tail"):
        target_file = None
        count = 10
        idx = 0
        while idx < len(args):
            if args[idx] == "-n" and idx + 1 < len(args):
                try:
                    count = int(args[idx + 1])
                except ValueError:
                    pass
                idx += 2
            else:
                target_file = args[idx]
                idx += 1
        if not target_file:
            output = f"{cmd}: missing file operand"
        else:
            target_path = resolve_path(target_file)
            if target_path in fs and fs[target_path]["type"] == "file":
                lines = fs[target_path]["content"].splitlines()
                if cmd == "head":
                    output = "\n".join(lines[:count])
                else:
                    output = "\n".join(lines[-count:])
            else:
                output = f"{cmd}: {target_file}: No such file or directory"

    elif cmd == "grep":
        if len(args) < 2:
            output = "grep: usage: grep <pattern> <file>"
        else:
            pattern = args[0].strip("'\"")
            target_file = args[-1]
            target_path = resolve_path(target_file)
            if target_path in fs and fs[target_path]["type"] == "file":
                lines = fs[target_path]["content"].splitlines()
                matched = [l for l in lines if pattern.lower() in l.lower()]
                output = "\n".join(matched) if matched else ""
            else:
                output = f"grep: {target_file}: No such file or directory"

    elif cmd == "find":
        search_dir = cwd
        name_pattern = None
        idx = 0
        while idx < len(args):
            if args[idx] == "-name" and idx + 1 < len(args):
                name_pattern = args[idx + 1].strip("'\"*")
                idx += 2
            elif not args[idx].startswith("-"):
                search_dir = resolve_path(args[idx])
                idx += 1
            else:
                idx += 1
        results = []
        for path_key in fs:
            if path_key.startswith(search_dir):
                basename = os.path.basename(path_key)
                if name_pattern is None or name_pattern in basename:
                    rel = path_key.replace(f"/home/{username}", "~")
                    results.append(rel)
        output = "\n".join(sorted(results)) if results else ""

    elif cmd == "rm":
        recursive = False
        files_to_remove = []
        for a in args:
            if a in ["-r", "-rf", "-f", "-fr"]:
                recursive = True
            elif a.startswith("-") and "r" in a:
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
                    # Remove recursively from fs dict
                    keys_to_del = [k for k in fs if k == target_path or k.startswith(target_path + "/")]
                    for k in keys_to_del:
                        del fs[k]
                    parent_dir = os.path.dirname(target_path)
                    base = os.path.basename(target_path)
                    if parent_dir in fs and base in fs[parent_dir]["children"]:
                        fs[parent_dir]["children"].remove(base)
            else:
                msgs.append(f"rm: cannot remove '{fname}': No such file or directory")
        output = "\n".join(msgs)

    elif cmd == "chmod":
        if len(args) < 2:
            output = "chmod: usage: chmod <mode> <file>"
        else:
            mode_arg = args[0]
            target_file = args[1]
            target_path = resolve_path(target_file)
            if target_path in fs:
                if "+x" in mode_arg or "755" in mode_arg or "777" in mode_arg:
                    fs[target_path]["mode"] = "755"
                    output = ""
                elif "-x" in mode_arg or "644" in mode_arg:
                    fs[target_path]["mode"] = "644"
                    output = ""
                else:
                    fs[target_path]["mode"] = mode_arg
                    output = ""
            else:
                output = f"chmod: cannot access '{target_file}': No such file or directory"

    elif cmd == "sudo":
        if len(args) >= 3 and args[0] == "chown":
            user_target = args[1]
            file_target = args[2]
            target_path = resolve_path(file_target)
            if target_path in fs:
                fs[target_path]["owner"] = user_target
                output = ""
            else:
                output = f"chown: cannot access '{file_target}': No such file or directory"
        else:
            output = f"sudo: {' '.join(args)}: command not found"

    elif cmd == "chown":
        if len(args) >= 2:
            user_target = args[0]
            file_target = args[1]
            target_path = resolve_path(file_target)
            if target_path in fs:
                fs[target_path]["owner"] = user_target
                output = ""
            else:
                output = f"chown: cannot access '{file_target}': No such file or directory"
        else:
            output = "chown: usage: chown <user> <file>"

    elif cmd.startswith("./"):
        script_name = cmd[2:]
        target_path = resolve_path(script_name)
        if target_path in fs:
            mode = fs[target_path].get("mode", "644")
            is_exec = ("x" in mode or mode in ("755", "777", "111", "755", "775"))
            if is_exec:
                script_content = fs[target_path]["content"]
                script_dir = os.path.dirname(target_path)
                created_file = None
                if "done.txt" in script_content:
                    created_file = os.path.join(script_dir, "done.txt")
                    fs[created_file] = {"type": "file", "owner": username, "mode": "644", "content": "muvaffaqiyatli"}
                    if "done.txt" not in fs[script_dir]["children"]:
                        fs[script_dir]["children"].append("done.txt")
                    output = "Skript ishga tushdi!"
                elif "result.txt" in script_content:
                    created_file = os.path.join(script_dir, "result.txt")
                    fs[created_file] = {"type": "file", "owner": username, "mode": "644", "content": "Tabriklaymiz, siz oxirgi bosqichga yetdingiz!"}
                    if "result.txt" not in fs[script_dir]["children"]:
                        fs[script_dir]["children"].append("result.txt")
                    output = "SUCCESS: result.txt created!"
                else:
                    output = "Execution finished."
            else:
                output = f"bash: ./{script_name}: Permission denied"
        else:
            output = f"bash: ./{script_name}: No such file or directory"

    elif cmd == "nano":
        if not args:
            output = "nano: missing file operand"
        else:
            target_path = resolve_path(args[0])
            content = ""
            if target_path in fs and fs[target_path]["type"] == "file":
                content = fs[target_path]["content"]
            return jsonify({
                "action": "open_editor",
                "path": target_path,
                "filename": os.path.basename(target_path),
                "content": content,
                "cwd": cwd
            })

    elif cmd == "echo":
        if ">" in raw_cmd:
            gt_idx = raw_cmd.index(">")
            echo_part = raw_cmd[:gt_idx]
            file_dest = raw_cmd[gt_idx + 1:].strip()
            text = echo_part.replace("echo", "", 1).strip().strip('"').strip("'")
            target_path = resolve_path(file_dest)
            parent_dir = os.path.dirname(target_path)
            if parent_dir in fs:
                base = os.path.basename(target_path)
                if base not in fs[parent_dir]["children"]:
                    fs[parent_dir]["children"].append(base)
                fs[target_path] = {"type": "file", "owner": username, "mode": "644", "content": text}
                output = ""
            else:
                output = f"bash: {file_dest}: No such file or directory"
        else:
            text = raw_cmd.replace("echo", "", 1).strip().strip('"').strip("'")
            output = text

    else:
        output = f"bash: {cmd}: command not found"

    return jsonify({"output": output, "cwd": cwd})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
