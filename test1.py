from priceBook import PriceBook

book = PriceBook()

# simulate two products

book.upsert({
    "url": "https://koodforosh.com/showads/8888",
    "name": "کود سولفات آمونیوم",
    "category": "کود سولفات",
    "price_per_kg": 67300,
})

# run again with a changed price to demo update:
book.upsert({
    "url": "https://koodforosh.com/showads/3167",
    "name": "تولید نیترات پتاسیم خلوص بالا",
    "category": "کود پتاس",
    "price_per_kg": 900,   # price changed
})

book.save()