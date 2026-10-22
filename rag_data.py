# Wissensbasis des Lieferdienstes: jeder Eintrag ist ein "Chunk" mit ID und Quelle
DOCS = [
    {"id": "v1", "source": "Lieferung", "text": "Die Standardlieferung dauert 2 bis 3 Werktage."},
    {"id": "v2", "source": "Lieferung", "text": "Expresslieferung ist innerhalb Hamburgs in 24 Stunden möglich und kostet 15 Euro Aufpreis."},
    {"id": "v3", "source": "Lieferung", "text": "Ab einem Bestellwert von 50 Euro ist die Standardlieferung kostenlos."},
    {"id": "v4", "source": "Rücksendung", "text": "Rücksendungen sind innerhalb von 14 Tagen nach Erhalt möglich. Das Rücksendeetikett finden Sie im Kundenkonto."},
    {"id": "v5", "source": "Zustellung", "text": "Wenn niemand zu Hause ist, hinterlässt der Fahrer eine Benachrichtigungskarte und versucht es am nächsten Werktag erneut."},
    {"id": "v6", "source": "Schäden", "text": "Beschädigte Pakete müssen innerhalb von 48 Stunden mit einem Foto gemeldet werden."},
    {"id": "v7", "source": "Zustellung", "text": "Wir liefern Montag bis Samstag zwischen 8 und 20 Uhr. Sonntags gibt es keine Zustellung."},
    {"id": "v8", "source": "Bezahlung", "text": "Sie können per Karte, PayPal oder Rechnung bezahlen. Rechnung ist nur für Stammkunden möglich."},
]

# Testfragen: welcher Chunk enthält die Antwort?
QUESTIONS = [
    {"question": "Wie lange dauert die Standardlieferung?", "expected": "v1"},
    {"question": "Was kostet Express?", "expected": "v2"},
    {"question": "Kann ich ein Paket zurückschicken?", "expected": "v4"},
    {"question": "Liefert ihr am Sonntag?", "expected": "v7"},
    {"question": "Was passiert, wenn ich nicht zu Hause bin?", "expected": "v5"},
]