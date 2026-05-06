def parse_car(url, rates):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        html = requests.get(url, headers=headers, timeout=30).text
        
        # ИСПРАВЛЕННОЕ РЕГУЛЯРНОЕ ВЫРАЖЕНИЕ
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)</script>', html)
        
        if not match:
            return {'success': False, 'error': 'JSON блок не найден'}
        
        data = json.loads(match.group(1))
        sku = data.get('props', {}).get('pageProps', {}).get('skuDetail', {})
        
        if not sku:
            return {'success': False, 'error': 'Данные авто не найдены'}
        
        # ЦЕНА (из числового поля sh_price в фэнях)
        price_fen = sku.get('source_sh_price', 0) or sku.get('sh_price', 0)
        price_cny = price_fen / 100 if price_fen else 0
        
        # Если цена не найдена - пробуем из car_info
        if price_cny == 0:
            car_info = sku.get('car_info', {})
            price_str = car_info.get('car_price', '')
            match_p = re.search(r'(\d+(?:\.\d+)?)', price_str)
            if match_p:
                price_cny = float(match_p.group(1)) * 10000
        
        # Название
        car_info = sku.get('car_info', {})
        series = car_info.get('series_name', '')
        model = car_info.get('car_name', '')
        title = f"{series} {model}".strip()
        
        # Год
        year = car_info.get('year', 0)
        
        # Пробег (из important_text)
        mileage_text = sku.get('important_text', '')
        m_match = re.search(r'(\d+(?:\.\d+)?)\s*万', mileage_text)
        if m_match:
            mileage_val = int(float(m_match.group(1)) * 10000)
            mileage = f"{mileage_val:,} км"
        else:
            mileage = "не указано"
        
        # Цвет
        color = car_info.get('body_color', 'не указан')
        
        # Двигатель и топливо
        power = sku.get('car_config_overview', {}).get('power', {})
        fuel_raw = power.get('fuel_form', '')
        fuel = 'Бензин' if fuel_raw == '汽油' else ('Дизель' if fuel_raw == '柴油' else fuel_raw)
        
        engine_raw = power.get('capacity', '0')
        e_match = re.search(r'(\d+(?:\.\d+)?)', engine_raw)
        if e_match:
            liters = float(e_match.group(1))
            engine_cc = int(liters * 1000) if liters < 10 else int(liters)
        else:
            engine_cc = 0
        engine_display = f"{engine_cc} см³" if engine_cc else "не указано"
        
        # Мощность
        hp_raw = power.get('horsepower', '')
        hp_match = re.search(r'(\d+)', str(hp_raw))
        horsepower = int(hp_match.group(1)) if hp_match else 0
        
        # Коробка
        gearbox_raw = power.get('gearbox_description', '')
        if '自动' in gearbox_raw or '手自' in gearbox_raw:
            gearbox = 'Автомат'
        elif '手动' in gearbox_raw:
            gearbox = 'Механика'
        elif '双离合' in gearbox_raw:
            gearbox = 'Робот'
        else:
            gearbox = gearbox_raw if gearbox_raw else 'не указано'
        
        # Привод
        manipulation = sku.get('car_config_overview', {}).get('manipulation', {})
        drive_raw = manipulation.get('driver_form', '')
        if '前置前驱' in drive_raw:
            drive = 'Передний'
        elif '前置四驱' in drive_raw:
            drive = 'Полный'
        else:
            drive = 'не указано'
        
        # Фото
        photos = sku.get('head_images', [])
        
        # ========== РАСЧЁТ СТОИМОСТИ ==========
        cny_rate = rates.get('CNY', 11.19)
        euro_rate = rates.get('EUR', 88.64)
        
        price_rub = price_cny * cny_rate
        delivery = 13000 * cny_rate
        commission = price_cny * 0.02 * cny_rate
        tax = (price_cny - 300000) * 0.13 * cny_rate if price_cny > 300000 else 0
        
        age = 2025 - year if year else 1
        if engine_cc <= 1000: rate = 3.0
        elif engine_cc <= 1500: rate = 3.4
        elif engine_cc <= 1800: rate = 4.0
        elif engine_cc <= 2300: rate = 4.4
        elif engine_cc <= 3000: rate = 5.0
        else: rate = 5.7
        
        if age <= 3:
            customs_eur = price_rub * 0.48 / euro_rate
        else:
            customs_eur = engine_cc * rate
        
        customs_rub = customs_eur * euro_rate
        total = price_rub + delivery + commission + tax + customs_rub + 5200 + 310000
        
        result_text = f"""🇨🇳 {title}
📅 Год: {year}
📍 Пробег: {mileage}
🎨 Цвет: {color}
⛽️ Топливо: {fuel}
🛠 Двигатель: {engine_display}
⚡ Мощность: {horsepower} л.с.
⚙️ Коробка: {gearbox}
🛞 Привод: {drive}
💰 Цена в Китае: {price_cny:,.0f} ¥
💲 ИТОГО с доставкой и таможней: {total:,.0f} ₽"""
        
        return {
            'success': True,
            'formatted_text': result_text,
            'archive_data': {
                'title': title, 'year': year, 'mileage': mileage, 'color': color,
                'fuel': fuel, 'engine_display': engine_display, 'horsepower': horsepower,
                'gearbox': gearbox, 'drive': drive, 'price_cny': price_cny,
                'total_cost': total, 'customs': {'eur': round(customs_eur, 0)},
                'photos': photos
            }
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}
