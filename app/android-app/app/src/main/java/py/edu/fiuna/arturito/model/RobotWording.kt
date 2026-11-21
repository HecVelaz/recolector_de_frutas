package py.edu.fiuna.arturito.model

/** Vocabulary for people. Protocol keys and ROS topic names keep their original spelling. */
fun mobileWording(text: String): String = text
    .replace("Base:", "Móvil:")
    .replace("La base", "El móvil")
    .replace("de la base", "del móvil")
    .replace("a la base", "al móvil")
    .replace("en la base", "en el móvil")
    .replace("la base", "el móvil")
