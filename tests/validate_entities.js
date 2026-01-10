/**
 * Walidator encji dla automatyzacji Home Assistant
 * Sprawdza spójność entity_id między automatyzacjami a definicjami sensorów
 */

const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const CONFIG_DIR = path.join(__dirname, '..', 'config');

// Custom YAML schema dla tagów Home Assistant
const HA_TAGS = ['include', 'include_dir_list', 'include_dir_merge_list',
                 'include_dir_named', 'include_dir_merge_named', 'secret', 'env_var'];
const haTypes = HA_TAGS.map(tag => new yaml.Type('!' + tag, {
  kind: 'scalar',
  construct: (data) => ({ _ha_tag: tag, value: data })
}));
const HA_SCHEMA = yaml.DEFAULT_SCHEMA.extend(haTypes);

// Encje zdefiniowane lokalnie (input_*, template sensors)
const localEntities = new Set();

// Encje używane w automatyzacjach
const usedEntities = new Set();

// Encje zewnętrzne (z integracji) - nie wymagają lokalnej definicji
const EXTERNAL_DOMAINS = [
  'sun', 'weather', 'person', 'zone', 'device_tracker',
  'huawei_solar', 'climate', 'water_heater', 'switch',
  'number', 'select', 'button', 'automation', 'script',
  'persistent_notification', 'notify', 'telegram_bot',
  'pyscript', 'shell_command', 'homeassistant'
];

// Znane encje zewnętrzne (z integracji Huawei, Aquarea, itp.)
const KNOWN_EXTERNAL_ENTITIES = [
  // Huawei Solar
  'sensor.akumulatory_stan_pojemnosci',
  'sensor.akumulatory_moc_ladowania_rozladowania',
  'sensor.falownik_moc_wyjsciowa_aktywna',
  'sensor.meter_active_power',
  'sensor.prognoza_pv_dzisiaj',
  'sensor.prognoza_pv_jutro',
  'sensor.energia_z_pv_dzisiaj',
  'sensor.energia_z_sieci_dzisiaj',
  'sensor.energia_do_sieci_dzisiaj',
  'sensor.energia_z_baterii_dzisiaj',
  'sensor.energia_do_baterii_dzisiaj',
  'sensor.zuzycie_energii_dzisiaj',
  'sensor.inverter_internal_temperature',
  'sensor.battery_temperature',
  'number.batteries_maximum_charging_power',
  'number.batteries_end_of_charge_soc',
  'number.batteries_end_of_discharge_soc',
  'number.batteries_grid_charge_cutoff_soc',
  'select.batteries_working_mode',
  'switch.batteries_force_charge_discharge',
  'switch.batteries_forcible_charge',
  'switch.batteries_forcible_discharge',
  'button.batteries_wakeup',

  // Aquarea (Panasonic)
  'climate.bodynek_nb_zone_1',
  'water_heater.bodynek_nb_tank',
  'switch.bodynek_nb_wymus_c_w_u',
  'sensor.bodynek_nb_temperatura_zewnetrzna',

  // RCE PSE
  'sensor.rce_pse_cena',
  'sensor.rce_pse_cena_jutro',

  // Pogoda
  'sensor.temperatura_zewnetrzna',
  'weather.home',

  // System
  'sun.sun',
  'persistent_notification.create',
  'automation.battery_algorithm_decision'
];

let errors = 0;
let warnings = 0;

console.log('='.repeat(60));
console.log('WALIDACJA ENCJI - Home Assistant Huawei Solar');
console.log('='.repeat(60));
console.log();

// 1. Zbierz encje zdefiniowane lokalnie
console.log('1. Zbieranie encji lokalnych...');

// input_numbers
try {
  const content = fs.readFileSync(path.join(CONFIG_DIR, 'input_numbers.yaml'), 'utf8');
  const data = yaml.load(content, { schema: HA_SCHEMA });
  if (data) {
    Object.keys(data).forEach(key => localEntities.add(`input_number.${key}`));
  }
  console.log(`   input_numbers.yaml: ${Object.keys(data || {}).length} encji`);
} catch (e) { console.log(`   [WARN] input_numbers.yaml: ${e.message}`); }

// input_boolean
try {
  const content = fs.readFileSync(path.join(CONFIG_DIR, 'input_boolean.yaml'), 'utf8');
  const data = yaml.load(content, { schema: HA_SCHEMA });
  if (data) {
    Object.keys(data).forEach(key => localEntities.add(`input_boolean.${key}`));
  }
  console.log(`   input_boolean.yaml: ${Object.keys(data || {}).length} encji`);
} catch (e) { console.log(`   [WARN] input_boolean.yaml: ${e.message}`); }

// input_text
try {
  const content = fs.readFileSync(path.join(CONFIG_DIR, 'input_text.yaml'), 'utf8');
  const data = yaml.load(content, { schema: HA_SCHEMA });
  if (data) {
    Object.keys(data).forEach(key => localEntities.add(`input_text.${key}`));
  }
  console.log(`   input_text.yaml: ${Object.keys(data || {}).length} encji`);
} catch (e) { console.log(`   [WARN] input_text.yaml: ${e.message}`); }

// input_select
try {
  const content = fs.readFileSync(path.join(CONFIG_DIR, 'input_select.yaml'), 'utf8');
  const data = yaml.load(content, { schema: HA_SCHEMA });
  if (data) {
    Object.keys(data).forEach(key => localEntities.add(`input_select.${key}`));
  }
  console.log(`   input_select.yaml: ${Object.keys(data || {}).length} encji`);
} catch (e) { console.log(`   [WARN] input_select.yaml: ${e.message}`); }

// template_sensors
try {
  const content = fs.readFileSync(path.join(CONFIG_DIR, 'template_sensors.yaml'), 'utf8');
  const data = yaml.load(content, { schema: HA_SCHEMA });
  if (Array.isArray(data)) {
    data.forEach(block => {
      if (block.sensor) {
        const sensors = Array.isArray(block.sensor) ? block.sensor : [block.sensor];
        sensors.forEach(s => {
          if (s.unique_id) {
            localEntities.add(`sensor.${s.unique_id}`);
          }
          if (s.name) {
            // Konwertuj nazwę na entity_id (uproszczone)
            const entityId = s.name.toLowerCase().replace(/[^a-z0-9]/g, '_').replace(/_+/g, '_');
            localEntities.add(`sensor.${entityId}`);
          }
        });
      }
      if (block.binary_sensor) {
        const sensors = Array.isArray(block.binary_sensor) ? block.binary_sensor : [block.binary_sensor];
        sensors.forEach(s => {
          if (s.unique_id) {
            localEntities.add(`binary_sensor.${s.unique_id}`);
          }
          if (s.name) {
            const entityId = s.name.toLowerCase().replace(/[^a-z0-9]/g, '_').replace(/_+/g, '_');
            localEntities.add(`binary_sensor.${entityId}`);
          }
        });
      }
    });
  }
  console.log(`   template_sensors.yaml: ${localEntities.size} encji (łącznie)`);
} catch (e) { console.log(`   [WARN] template_sensors.yaml: ${e.message}`); }

// Dodaj znane encje zewnętrzne
KNOWN_EXTERNAL_ENTITIES.forEach(e => localEntities.add(e));

console.log(`   Łącznie znanych encji: ${localEntities.size}`);
console.log();

// 2. Zbierz encje używane w automatyzacjach
console.log('2. Zbieranie encji używanych w automatyzacjach...');

const AUTOMATION_FILES = [
  'automations_battery.yaml',
  'automations.yaml',
  'automations_errors.yaml'
];

function extractEntities(obj, entities) {
  if (!obj) return;

  if (typeof obj === 'string') {
    // Sprawdź czy to entity_id
    if (obj.match(/^[a-z_]+\.[a-z0-9_]+$/)) {
      entities.add(obj);
    }
    // Szukaj entity_id w szablonach Jinja2
    const matches = obj.matchAll(/states\(['"]([a-z_]+\.[a-z0-9_]+)['"]\)/g);
    for (const match of matches) {
      entities.add(match[1]);
    }
    const matches2 = obj.matchAll(/is_state\(['"]([a-z_]+\.[a-z0-9_]+)['"]/g);
    for (const match of matches2) {
      entities.add(match[1]);
    }
    const matches3 = obj.matchAll(/state_attr\(['"]([a-z_]+\.[a-z0-9_]+)['"]/g);
    for (const match of matches3) {
      entities.add(match[1]);
    }
    return;
  }

  if (Array.isArray(obj)) {
    obj.forEach(item => extractEntities(item, entities));
    return;
  }

  if (typeof obj === 'object') {
    // Bezpośrednie pola entity_id
    if (obj.entity_id) {
      if (Array.isArray(obj.entity_id)) {
        obj.entity_id.forEach(e => {
          if (typeof e === 'string') entities.add(e);
        });
      } else if (typeof obj.entity_id === 'string') {
        entities.add(obj.entity_id);
      }
    }

    // Rekursywnie przeszukuj obiekt
    Object.values(obj).forEach(value => extractEntities(value, entities));
  }
}

for (const file of AUTOMATION_FILES) {
  try {
    const content = fs.readFileSync(path.join(CONFIG_DIR, file), 'utf8');
    const automations = yaml.load(content, { schema: HA_SCHEMA });

    if (Array.isArray(automations)) {
      automations.forEach(auto => extractEntities(auto, usedEntities));
    }

    console.log(`   ${file}: przeanalizowany`);
  } catch (e) {
    console.log(`   [WARN] ${file}: ${e.message}`);
  }
}

console.log(`   Łącznie używanych encji: ${usedEntities.size}`);
console.log();

// 3. Sprawdź brakujące encje
console.log('3. Sprawdzanie brakujących encji...');

const missingEntities = [];
const externalEntities = [];

for (const entity of usedEntities) {
  // Pomijaj domeny zewnętrzne
  const domain = entity.split('.')[0];
  if (EXTERNAL_DOMAINS.includes(domain)) {
    externalEntities.push(entity);
    continue;
  }

  // Sprawdź czy encja jest zdefiniowana lokalnie
  if (!localEntities.has(entity)) {
    missingEntities.push(entity);
  }
}

if (missingEntities.length > 0) {
  console.log(`   [WARN] Potencjalnie brakujące encje (${missingEntities.length}):`);
  missingEntities.sort().forEach(e => {
    console.log(`          - ${e}`);
    warnings++;
  });
} else {
  console.log('   [PASS] Wszystkie encje są zdefiniowane lub zewnętrzne');
}

console.log();

// 4. Sprawdź duplikaty unique_id
console.log('4. Sprawdzanie duplikatów unique_id...');

const uniqueIds = new Map();
try {
  const content = fs.readFileSync(path.join(CONFIG_DIR, 'template_sensors.yaml'), 'utf8');
  const data = yaml.load(content, { schema: HA_SCHEMA });

  if (Array.isArray(data)) {
    data.forEach((block, blockIdx) => {
      ['sensor', 'binary_sensor'].forEach(type => {
        if (block[type]) {
          const sensors = Array.isArray(block[type]) ? block[type] : [block[type]];
          sensors.forEach((s, idx) => {
            if (s.unique_id) {
              if (uniqueIds.has(s.unique_id)) {
                console.log(`   [FAIL] Duplikat unique_id: ${s.unique_id}`);
                errors++;
              } else {
                uniqueIds.set(s.unique_id, `${type}[${blockIdx}][${idx}]`);
              }
            }
          });
        }
      });
    });
  }

  if (errors === 0) {
    console.log(`   [PASS] Brak duplikatów unique_id (${uniqueIds.size} unikalnych)`);
  }
} catch (e) {
  console.log(`   [WARN] ${e.message}`);
}

console.log();
console.log('='.repeat(60));
console.log(`PODSUMOWANIE: ${warnings} WARN, ${errors} FAIL`);
console.log('='.repeat(60));

if (errors > 0) {
  process.exit(1);
}
