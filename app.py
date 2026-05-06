import os
import re
import json
import requests
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ========== HTML ИНТЕРФЕЙС ==========
HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>🚗 Китайский автопарсер</title>
    <style>
        body { font-family: Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; margin: 0; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; border-radius: 20px; padding: 30px; margin-bottom: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
        h1 { color: #667eea; margin-top: 0; }
        input { width: 70%; padding: 12px; font-size: 16px; border: 2px solid #ddd; border-radius: 10px; }
        button { padding: 12px 24px; background: #667eea; color: white; border: none; border-radius: 10px; cursor: pointer; margin: 5px; }
        button:hover { background: #5a67d8; }
        .result { background: #f8f9fa; border-radius: 15px; padding: 20px; margin-top: 20px; display: none; }
        .price { font-size: 28px; font-weight: bold; color: #10b981; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .item { background: white; padding: 12px; border-radius: 10px; border-left: 4px solid #667eea; }
        .label { font-size: 12px; color: #888; }
        .value { font-size: 18px; font-weight: bold; }
        .photos { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 10px; margin-top: 20px; }
        .photos img { width: 100%; height: 80px; object-fit: cover; border-radius: 8px; cursor: pointer; }
        .tabs { display: flex; gap: 10px; margin: 20px 0; border-bottom: 2px solid #ddd; }
        .tab { padding: 10px 20px; background: none; color: #666; border: none; cursor: pointer; }
        .tab.active { color: #667eea; border-bottom: 3px solid #667eea; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .loader { display: inline-block; width: 20px; height: 20px; border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%; animation: spin 1s linear infinite; margin-right: 10px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .error { background: #fee; color: #c00; padding: 15px; border-radius: 10px; }
        .rate-input { width: 100px; padding: 8px; margin: 0 5px; text-align: center; }
    </style>
</head>
<body>
<div class="container">
    <div class="card">
        <h1>🚗 Китайский автопарсер</h1>
        <p>Вставь ссылку на авто с dongchedi.com — получи расчет полной стоимости под ключ</p>
        <input type="text" id="url" placeholder="https://www.dongchedi.com/usedcar/..." value="https://www.dongchedi.com/usedcar/23619795">
        <div style="margin: 15px 0;">
            <span>📈 Курсы:</span>
            <input type="number" id="cny" step="0.01" value="11.19" class="rate-input"> CNY→₽
            <input type="number" id="eur" step="0.01" value="88.64" class="rate-input"> EUR→₽
        </div>
        <div>
            <button onclick="parseCar()">🔍 Получить данные</button>
            <button onclick="downloadZip()">📦 Скачать ZIP</button>
        </div>
        <div id="result" class="result"></div>
    </div>
</div>

<script>
    async function parseCar() {
        const url = document.getElementById('url').value;
        if (!url) { alert('Введи ссылку'); return; }
        
        const btn = event.target;
        btn.innerHTML = '<span class="loader"></span> Загрузка...';
        btn.disabled = true;
        
        const resultDiv = document.getElementById('result');
        resultDiv.innerHTML = '<div style="text-align:center">⏳ Парсинг... Это может занять 10-30 секунд</div>';
        resultDiv.style.display = 'block';
        
        try {
            const res = await fetch('/api/parse', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: url,
                    rates: { CNY: parseFloat(document.getElementById('cny').value), EUR: parseFloat(document.getElementById('eur').value) }
                })
            });
            const data = await res.json();
            
            if (data.success) {
                displayResult(data);
            } else {
                resultDiv.innerHTML = `<div class="error">❌ ${data.error}</div>`;
            }
        } catch(e) {
            resultDiv.innerHTML = `<div class="error">❌ Ошибка: ${e.message}</div>`;
        } finally {
            btn.innerHTML = '🔍 Получить данные';
            btn.disabled = false;
        }
    }
    
    function displayResult(data) {
        const d = data.archive_data;
        const html = `
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
                <h2>${d.title || 'Автомобиль'}</h2>
                <div class="price">${Math.round(d.total_cost).toLocaleString()} ₽</div>
            </div>
            <div class="tabs">
                <button class="tab active" onclick="showTab('specs')">📋 Характеристики</button>
                <button class="tab" onclick="showTab('cost')">💰 Расчет</button>
                <button class="tab" onclick="showTab('photos')">📸 Фото (${d.photos?.length || 0})</button>
            </div>
            <div id="tab-specs" class="tab-content active">
                <div class="grid">
                    <div class="item"><div class="label">📅 Год</div><div class="value">${d.year || '-'}</div></div>
                    <div class="item"><div class="label">📍 Пробег</div><div class="value">${d.mileage || '-'}</div></div>
                    <div class="item"><div class="label">🎨 Цвет</div><div class="value">${d.color || '-'}</div></div>
                    <div class="item"><div class="label">⛽️ Топливо</div><div class="value">${d.fuel || '-'}</div></div>
                    <div class="item"><div class="label">🛠 Двигатель</div><div class="value">${d.engine_display || '-'}</div></div>
                    <div class="item"><div class="label">⚡ Мощность</div><div class="value">${d.horsepower || '-'} л.с.</div></div>
                    <div class="item"><div class="label">⚙️ Коробка</div><div class="value">${d.gearbox || '-'}</div></div>
                    <div class="item"><div class="label">🛞 Привод</div><div class="value">${d.drive || '-'}</div></div>
                    <div class="item"><div class="label">🇨🇳 Цена в Китае</div><div class="value">${d.price_cny?.toLocaleString()} ¥</div></div>
                </div>
            </div>
            <div id="tab-cost" class="tab-content">
                <div class="grid">
                    <div class="item"><div class="label">Цена в Китае</div><div class="value">${(d.price_cny * (document.getElementById('cny').value || 11.19)).toLocaleString()} ₽</div></div>
                    <div class="item"><div class="label">Доставка (13000¥)</div><div class="value">${(13000 * (document.getElementById('cny').value || 11.19)).toLocaleString()} ₽</div></div>
                    <div class="item"><div class="label">Комиссия 2%</div><div class="value">${(d.price_cny * 0.02 * (document.getElementById('cny').value || 11.19)).toLocaleString()} ₽</div></div>
                    <div class="item"><div class="label">Таможня</div><div class="value">${(d.customs?.eur * (document.getElementById('eur').value || 88.64)).toLocaleString()} ₽</div></div>
                    <div class="item"><div class="label">Утильсбор</div><div class="value">5 200 ₽</div></div>
                    <div class="item"><div class="label">Брокерские услуги</div><div class="value">310 000 ₽</div></div>
                    <div class="item"><div class="label" style="font-size:16px; color:#10b981;">💰 ИТОГО</div><div class="value" style="color:#10b981; font-size:24px;">${Math.round(d.total_cost).toLocaleString()} ₽</div></div>
                </div>
            </div>
            <div id="tab-photos" class="tab-content">
                <div class="photos">${(d.photos || []).slice(0, 20).map(url => `<img src="${url}" onerror="this.style.display='none'">`).join('') || '<p>Нет фото</p>'}</div>
            </div>
            <div style="margin-top:20px; padding:15px; background:#e8e8e8; border-radius:10px; white-space:pre-wrap; font-size:12px;">${data.formatted_text || ''}</div>
        `;
        document.getElementById('result').innerHTML = html;
        document.getElementById('result').style.display = 'block';
    }
    
    function showTab(tab) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        event.target.classList.add('active');
        document.getElementById(`tab-${tab}`).classList.add('active');
    }
    
    async function downloadZip() {
        const url = document.getElementById('url').value;
        if (!url) { alert('Введи ссылку'); return; }
        const res = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: url,
                rates: { CNY: parseFloat(document.getElementById('cny').value), EUR: parseFloat(document.getElementById('eur').value) }
            })
        });
        const blob = await res.blob();
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `car_${Date.now()}.zip`;
        a.click();
    }
</script>
</body>
</html>
'''

# ========== ПАРСЕР ==========
def parse_car(url, rates):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        html = requests.get(url, headers=headers, timeout=30).text
        
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if not match:
            return {'success': False, 'error': 'JSON не найден'}
        
        data = json.loads(match.group(1))
        sku = data.get('props', {}).get('pageProps', {}).get('skuDetail', {})
        if not sku:
            return {'success': False, 'error': 'Данные авто не найдены'}
        
        # Цена
        price_cny = sku.get('sh_price', 0) / 100
        if price_cny == 0:
            car_info = sku.get('car_info', {})
            price_str = car_info.get('car_price', '')
            match_p = re.search(r'(\d+(?:\.\d+)?)', price_str)
            if match_p:
                price_cny = float(match_p.group(1)) * 10000
        
        # Название
        car_info = sku.get('car_info', {})
        title = f"{car_info.get('series_name', '')} {car_info.get('car_name', '')}".strip()
        
        # Пробег
        mileage_text = sku.get('important_text', '')
        m_match = re.search(r'(\d+(?:\.\d+)?)\s*万', mileage_text)
        mileage = f"{int(float(m_match.group(1)) * 10000):,} км" if m_match else "не указано"
        
        # Двигатель
        power = sku.get('car_config_overview', {}).get('power', {})
        engine_raw = power.get('capacity', '0')
        e_match = re.search(r'(\d+(?:\.\d+)?)', engine_raw)
        engine_cc = int(float(e_match.group(1)) * 1000) if e_match else 0
        
        # Мощность
        hp_raw = power.get('horsepower', '')
        hp_match = re.search(r'(\d+)', str(hp_raw))
        horsepower = int(hp_match.group(1)) if hp_match else 0
        
        # Фото
        photos = sku.get('head_images', [])
        
        # Расчет таможни
        cny_rate = rates.get('CNY', 11.19)
        euro_rate = rates.get('EUR', 88.64)
        price_rub = price_cny * cny_rate
        delivery = 13000 * cny_rate
        commission = price_cny * 0.02 * cny_rate
        tax = (price_cny - 300000) * 0.13 * cny_rate if price_cny > 300000 else 0
        
        year = car_info.get('year', 0)
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
        
        result_text = f"🇨🇳 {title}\n📅 Год: {year}\n📍 Пробег: {mileage}\n💰 Цена: {total:,.0f} ₽"
        
        return {
            'success': True,
            'formatted_text': result_text,
            'archive_data': {
                'title': title, 'year': year, 'mileage': mileage,
                'color': car_info.get('body_color', '-'),
                'fuel': {'汽油':'Бензин','柴油':'Дизель'}.get(power.get('fuel_form',''), 'Бензин'),
                'engine_display': f"{engine_cc} см³" if engine_cc else '-',
                'horsepower': horsepower,
                'gearbox': {'手动':'Механика','自动':'Автомат'}.get(power.get('gearbox_description',''), '-'),
                'drive': {'前置前驱':'Передний','前置四驱':'Полный'}.get(sku.get('car_config_overview',{}).get('manipulation',{}).get('driver_form',''), '-'),
                'price_cny': price_cny,
                'total_cost': total,
                'customs': {'eur': round(customs_eur, 0)},
                'photos': photos
            }
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ========== ЗАПУСК ==========
@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/api/parse', methods=['POST'])
def api_parse():
    data = request.get_json()
    if not data or not data.get('url'):
        return jsonify({'success': False, 'error': 'URL обязателен'})
    return jsonify(parse_car(data['url'], data.get('rates', {})))

@app.route('/api/download', methods=['POST'])
def api_download():
    data = request.get_json()
    if not data or not data.get('url'):
        return jsonify({'success': False, 'error': 'URL обязателен'}), 400
    result = parse_car(data['url'], data.get('rates', {}))
    if not result.get('success'):
        return jsonify(result), 500
    
    import io, zipfile
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, 'w') as zf:
        zf.writestr('info.txt', result['formatted_text'].encode('utf-8'))
        zf.writestr('data.json', json.dumps(result['archive_data'], ensure_ascii=False, indent=2))
        for i, url in enumerate(result['archive_data'].get('photos', [])[:10]):
            try:
                img = requests.get(url, timeout=10).content
                zf.writestr(f'photo_{i+1}.jpg', img)
            except:
                pass
    memory.seek(0)
    return send_file(memory, as_attachment=True, download_name='car.zip', mimetype='application/zip')

from flask import send_file

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
