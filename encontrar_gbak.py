import winreg
import os 

possiveis_servicos = [
    r"SYSTEM\CurrentControlSet\Services\FirebirdServerDefaultInstance",
    r"SYSTEM\CurrentControlSet\Services\FirebirdGuardianDefaultInstance",
    r"SYSTEM\CurrentControlSet\Services\FirebirdServer"
]

gbak_path = None

for servico in possiveis_servicos:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, servico) as key:
            image_path, _ = winreg.QueryValueEx(key, "ImagePath")
            image_path = image_path.strip('"')

            pasta_firebird = os.path.dirname(image_path)
            gbak_test = os.path.join(pasta_firebird, "gbak.exe")

            if os.path.exists(gbak_test):
                gbak_path = gbak_test
                break
    except FileNotFoundError:
        continue

