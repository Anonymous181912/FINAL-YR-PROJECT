from PIL import Image, ImageDraw, ImageFont

font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 30)
bold = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 34)

reports = [
    ("report_jan", "12/01/2026", "13.8", "95", "88"),
    ("report_apr", "10/04/2026", "13.2", "112", "87"),
    ("report_jul", "10/07/2026", "12.6", "128", "86"),
]

for name, date, hb, glu, mcv in reports:
    img = Image.new("RGB", (1100, 620), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 30), "DEMO PATHOLOGY LAB - HAEMATOLOGY", font=bold, fill="black")
    d.text((40, 100), "Patient Name: Demo Patient", font=font, fill="black")
    d.text((40, 145), "Collection Date: " + date, font=font, fill="black")
    d.text((40, 190), "Report Date: " + date, font=font, fill="black")
    d.text((40, 270), "TEST          RESULT     UNIT      REF RANGE", font=bold, fill="black")
    rows = [
        ("Hemoglobin", hb, "g/dL", "13 - 17"),
        ("Fasting Blood Glucose", glu, "mg/dL", "70 - 100"),
        ("MCV", mcv, "fL", "81 - 101"),
    ]
    y = 340
    for t, v, u, r in rows:
        d.text((40, y), f"{t}   {v}   {u}   {r}", font=font, fill="black")
        y += 60
    img.save(name + ".png")
    print("saved", name + ".png")
