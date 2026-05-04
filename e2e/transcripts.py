# Test transcripts for E2E language detection tests

# courtesy of https://www.gutenberg.org/files/2701/2701-h/2701-h.htm#link2HCH0001
moby_dick_text = (
    "Call me Ishmael. Some years ago - never mind how long precisely - having little or no money "
    "in my purse, and nothing particular to interest me on shore, I thought I would sail about a "
    "little and see the watery part of the world. It is a way I have of driving off the spleen "
    "and regulating the circulation. Whenever I find myself growing grim about the mouth; whenever "
    "it is a damp, drizzly November in my soul; whenever I find myself involuntarily pausing before "
    "coffin warehouses, and bringing up the rear of every funeral I meet; and especially whenever "
    "my hypos get such an upper hand of me, that it requires a strong moral principle to prevent me "
    "from deliberately stepping into the street, and methodically knocking people's hats off - then, "
    "I account it high time to get to sea as soon as I can. This is my substitute for pistol and ball. "
    "With a philosophical flourish Cato throws himself upon his sword; I quietly take to the ship. "
    "There is nothing surprising in this. If they but knew it, almost all men in their degree, some "
    "time or other, cherish very nearly the same feelings towards the ocean with me."
)

# English transcript - should be summarized in English
english_transcript = """
Wei: Good morning everyone, let's start the meeting.
Nina: Thanks Wei. I wanted to discuss the Q4 roadmap today.
Fang: Sure, I've prepared the slides. We need to focus on three main areas.
Wei: Perfect. Let's start with the infrastructure updates.
Nina: Our team has completed the migration to the new cloud provider. Performance improved by 40%.
Fang: That's great news. What about the security audit?
Wei: The audit is scheduled for next week. Ming will be leading that effort.
Nina: We should also discuss the budget allocation for the new hires.
Fang: I agree. We need at least three more engineers for the mobile team.
Wei: Let's schedule a follow-up meeting to finalize the budget. Thanks everyone for joining today.
"""

# French transcript (~10% English) - should be summarized in French
french_transcript = """
Marie: Bonjour à tous, commençons la réunion.
Pierre: Merci Marie. Je voulais discuter du planning du projet aujourd'hui.
Sophie: Bien sûr, j'ai préparé les documents. Nous devons nous concentrer sur trois domaines principaux.
Marie: Parfait. Commençons par les mises à jour techniques.
Pierre: Notre équipe a terminé la migration vers le nouveau serveur cloud. Les performances se sont améliorées de 35%.
Sophie: C'est une excellente nouvelle. Qu'en est-il de l'audit de sécurité?
Marie: L'audit est prévu pour la semaine prochaine. Jean sera responsable de cet effort.
Pierre: Nous devrions également discuter du budget pour les nouvelles embauches.
Sophie: Je suis d'accord. On a besoin de plus de développeurs seniors.
Marie: OK, planifions une réunion de suivi pour finaliser le budget. Merci à tous!
"""

# German transcript (~10% English) - should be summarized in German
german_transcript = """
Klaus: Guten Morgen zusammen, lasst uns mit der Besprechung beginnen.
Anna: Danke Klaus. Ich wollte heute über die Projektziele sprechen.
Michael: Natürlich, ich habe die Präsentation vorbereitet. Wir müssen uns auf drei Hauptbereiche konzentrieren.
Klaus: Perfekt. Beginnen wir mit den technischen Aktualisierungen.
Anna: Unser Team hat die Migration zum neuen Server abgeschlossen. Die Leistung hat sich um 45% verbessert.
Michael: Das sind großartige Neuigkeiten. Was ist mit der Sicherheitsprüfung?
Klaus: Die Prüfung ist für nächste Woche geplant. Stefan wird die Projektleitung übernehmen.
Anna: Wir sollten auch das Budget für neue Mitarbeiter besprechen.
Michael: Einverstanden. Mindestens drei Senior Entwickler für das Mobile Team.
Klaus: Okay, planen wir ein Folgetreffen. Danke an alle fürs Teilnehmen!
"""

# Spanish transcript (~10% English) - should be summarized in Spanish
spanish_transcript = """
Carlos: Buenos días a todos, empecemos la reunión.
María: Gracias Carlos. Quería hablar sobre el plan del proyecto hoy.
Juan: Por supuesto, he preparado los documentos. Necesitamos enfocarnos en tres áreas principales.
Carlos: Perfecto. Comencemos con las actualizaciones técnicas.
María: Nuestro equipo ha completado la migración al nuevo servidor. El rendimiento mejoró un 40%.
Juan: Son excelentes noticias. ¿Qué hay de la auditoría de seguridad?
Carlos: La auditoría está programada para la próxima semana. Pedro liderará ese esfuerzo.
María: También deberíamos revisar el presupuesto para las nuevas contrataciones.
Juan: Estoy de acuerdo. Necesitamos al menos cuatro desarrolladores full-stack más.
Carlos: OK, programemos una reunión de seguimiento para finalizar el presupuesto. Gracias a todos!
"""

# Italian transcript (~10% English) - should be summarized in Italian
italian_transcript = """
Marco: Buongiorno a tutti, iniziamo la riunione.
Giulia: Grazie Marco. Volevo discutere del piano del progetto oggi.
Luca: Certo, ho preparato i documenti. Dobbiamo concentrarci su tre aree principali.
Marco: Perfetto. Iniziamo con gli aggiornamenti tecnici.
Giulia: Il nostro team ha completato la migrazione al nuovo server cloud. Le prestazioni sono migliorate del 38%.
Luca: Ottime notizie! Che ne è del controllo di sicurezza?
Marco: L'audit è programmato per la prossima settimana. Paolo sarà il responsabile di questo progetto.
Giulia: Dovremmo anche discutere il budget per le nuove assunzioni.
Luca: Sono d'accordo. Almeno tre sviluppatori senior per supportare il team mobile.
Marco: OK, pianifichiamo un incontro di follow-up per finalizzare il budget. Grazie a tutti!
"""
