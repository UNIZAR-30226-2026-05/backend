import security

# Pedir al usuario que introduzca la contraseña
password = input("Introduce la contraseña: ")

# Obtener el hash de la contraseña usando la función del archivo security.py
hashed_password = security.obtener_hash_password(password)

# Mostrar el hash resultante
print("El hash de la contraseña es:", hashed_password)