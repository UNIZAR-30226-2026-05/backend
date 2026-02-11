query = "SELECT nombre, password FROM USUARIOS.USUARIO WHERE nombre = %s"
        
cursor.execute(query, (nombre,))
usuario = cursor.fetchone()