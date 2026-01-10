/**
 * Walidator YAML dla automatyzacji Home Assistant
 * Sprawdza składnię wszystkich plików YAML w katalogu config/
 */

const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const CONFIG_DIR = path.join(__dirname, '..', 'config');

// Custom YAML schema dla tagów Home Assistant
const HA_TAGS = [
  'include',
  'include_dir_list',
  'include_dir_merge_list',
  'include_dir_named',
  'include_dir_merge_named',
  'secret',
  'env_var'
];

const haTypes = HA_TAGS.map(tag => new yaml.Type('!' + tag, {
  kind: 'scalar',
  construct: (data) => ({ _ha_tag: tag, value: data })
}));

const HA_SCHEMA = yaml.DEFAULT_SCHEMA.extend(haTypes);

// Pliki do walidacji
const YAML_FILES = [
  'automations_battery.yaml',
  'automations.yaml',
  'automations_errors.yaml',
  'template_sensors.yaml',
  'input_numbers.yaml',
  'input_boolean.yaml',
  'input_text.yaml',
  'input_select.yaml',
  'configuration.yaml',
  'scripts.yaml',
  'scenes.yaml',
  'utility_meter.yaml',
  'logger.yaml'
];

let errors = 0;
let warnings = 0;
let passed = 0;

console.log('='.repeat(60));
console.log('WALIDACJA YAML - Home Assistant Huawei Solar');
console.log('='.repeat(60));
console.log();

for (const file of YAML_FILES) {
  const filePath = path.join(CONFIG_DIR, file);

  if (!fs.existsSync(filePath)) {
    console.log(`[SKIP] ${file} - plik nie istnieje`);
    continue;
  }

  try {
    const content = fs.readFileSync(filePath, 'utf8');

    // Parsuj YAML z obsługą tagów HA
    const docs = yaml.loadAll(content, { schema: HA_SCHEMA });

    // Sprawdź czy nie jest pusty
    if (!docs || docs.length === 0 || (docs.length === 1 && docs[0] === null)) {
      console.log(`[WARN] ${file} - plik jest pusty`);
      warnings++;
      continue;
    }

    // Dodatkowa walidacja dla automatyzacji
    if (file.startsWith('automations')) {
      validateAutomations(file, docs[0]);
    }

    // Dodatkowa walidacja dla template_sensors
    if (file === 'template_sensors.yaml') {
      validateTemplateSensors(file, docs[0]);
    }

    console.log(`[PASS] ${file} - poprawna składnia YAML`);
    passed++;

  } catch (e) {
    console.log(`[FAIL] ${file} - błąd składni:`);
    console.log(`       ${e.message}`);
    errors++;
  }
}

/**
 * Walidacja automatyzacji HA
 */
function validateAutomations(file, automations) {
  if (!Array.isArray(automations)) {
    console.log(`[WARN] ${file} - oczekiwano tablicy automatyzacji`);
    warnings++;
    return;
  }

  let autoErrors = 0;

  for (let i = 0; i < automations.length; i++) {
    const auto = automations[i];

    // Sprawdź wymagane pola
    if (!auto.id && !auto.alias) {
      console.log(`[WARN] ${file}[${i}] - brak id lub alias`);
      warnings++;
    }

    if (!auto.trigger && !auto.triggers) {
      console.log(`[WARN] ${file}[${i}] ${auto.alias || auto.id || ''} - brak trigger/triggers`);
      warnings++;
      autoErrors++;
    }

    if (!auto.action && !auto.actions) {
      console.log(`[WARN] ${file}[${i}] ${auto.alias || auto.id || ''} - brak action/actions`);
      warnings++;
      autoErrors++;
    }

    // Sprawdź entity_id w triggerach
    const triggers = auto.trigger || auto.triggers || [];
    const triggerList = Array.isArray(triggers) ? triggers : [triggers];

    for (const trigger of triggerList) {
      if (trigger && trigger.entity_id) {
        const entityIds = Array.isArray(trigger.entity_id) ? trigger.entity_id : [trigger.entity_id];
        for (const entityId of entityIds) {
          if (typeof entityId === 'string' && !isValidEntityId(entityId)) {
            console.log(`[WARN] ${file} "${auto.alias || auto.id}" - nieprawidłowy entity_id w trigger: ${entityId}`);
            warnings++;
          }
        }
      }
    }
  }

  if (autoErrors === 0) {
    console.log(`       ${automations.length} automatyzacji zwalidowanych`);
  }
}

/**
 * Walidacja template sensors
 */
function validateTemplateSensors(file, sensors) {
  if (!Array.isArray(sensors)) {
    console.log(`[WARN] ${file} - oczekiwano tablicy sensorów`);
    warnings++;
    return;
  }

  let sensorCount = 0;
  let binaryCount = 0;

  for (const block of sensors) {
    if (block.sensor) {
      sensorCount += Array.isArray(block.sensor) ? block.sensor.length : 1;
    }
    if (block.binary_sensor) {
      binaryCount += Array.isArray(block.binary_sensor) ? block.binary_sensor.length : 1;
    }
  }

  console.log(`       ${sensorCount} sensorów, ${binaryCount} binary_sensors`);
}

/**
 * Sprawdź czy entity_id ma poprawny format
 */
function isValidEntityId(entityId) {
  // Pomijamy szablony Jinja2
  if (entityId.includes('{{') || entityId.includes('{%')) {
    return true;
  }

  // Format: domain.entity_name
  const pattern = /^[a-z_]+\.[a-z0-9_]+$/;
  return pattern.test(entityId);
}

console.log();
console.log('='.repeat(60));
console.log(`PODSUMOWANIE: ${passed} PASS, ${warnings} WARN, ${errors} FAIL`);
console.log('='.repeat(60));

if (errors > 0) {
  process.exit(1);
}
