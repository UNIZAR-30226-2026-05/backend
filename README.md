## CREACIÓN DE LA BASE DE DATOS
Para la creación de la base de datos hemos planteado un esquema entidad relación y obtenido una serie de relaciones. Para organizar mejor cada tabla hemos implementado tres esquemas en la BD:
- **Juego:** recoge las tablas que contienen información base del juego, es decir, información que una vez añadida no se piensa modificar a no ser que se cambien las características del juego (minijuegos, objetos, personajes, ...)

- **Usuarios:** recoge la información relativa a los usuarios almacenados en el sistema, sus amistades y las sesiones activas

- **Partidas:** compuesta por toda aquella información sobre partidas activas en el servidor. Dicha información es principalmente volátil ya que no se pretende que este almacenada más allá de la duración de la partida

PARA CONTROLAR EL CONTENEDOR HAY QEU AÑADIR NUESTRO USUARIO AL GRUPO DOCKER:
sudo usermod -aG docker $USER
newgrp docker