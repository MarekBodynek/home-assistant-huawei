/**
 * Testy automatyzacji Home Assistant
 * Sprawdza strukturę triggerów, warunków i akcji
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

let passed = 0;
let failed = 0;
let warnings = 0;

console.log('='.repeat(60));
console.log('TESTY AUTOMATYZACJI - Home Assistant Huawei Solar');
console.log('='.repeat(60));
console.log();

// ============================================
// TESTY automations_battery.yaml
// ============================================

console.log('## automations_battery.yaml');
console.log();

try {
  const content = fs.readFileSync(path.join(CONFIG_DIR, 'automations_battery.yaml'), 'utf8');
  const automations = yaml.load(content, { schema: HA_SCHEMA });

  // Test 1: Każda automatyzacja ma unikalne ID
  const ids = automations.map(a => a.id).filter(id => id);
  const uniqueIds = new Set(ids);
  if (ids.length === uniqueIds.size) {
    console.log('[PASS] Wszystkie automatyzacje mają unikalne ID');
    passed++;
  } else {
    console.log('[FAIL] Duplikaty ID automatyzacji');
    failed++;
  }

  // Test 2: Główna automatyzacja algorytmu istnieje (szukaj po alias)
  const mainAlgo = automations.find(a => a.alias && a.alias.includes('Wykonaj strategię (co 1h)'));
  if (mainAlgo) {
    console.log('[PASS] Główna automatyzacja algorytmu istnieje (Wykonaj strategię co 1h)');
    passed++;

    // Test 2a: Trigger co godzinę (time_pattern z hours=* i minutes=0/00)
    const triggers = mainAlgo.trigger || mainAlgo.triggers || [];
    const timeTrigger = triggers.find(t => t.trigger === 'time_pattern' || t.platform === 'time_pattern');
    const minutesValid = timeTrigger && (
      timeTrigger.minutes === 0 ||
      timeTrigger.minutes === '0' ||
      timeTrigger.minutes === '00' ||
      timeTrigger.minutes === '/1'
    );
    if (minutesValid && (timeTrigger.hours === '*' || !timeTrigger.hours)) {
      console.log('[PASS] Algorytm uruchamia się co godzinę (time_pattern hours=* minutes=00)');
      passed++;
    } else {
      console.log(`[WARN] Algorytm nie ma triggera co godzinę (minutes=${timeTrigger?.minutes})`);
      warnings++;
    }

    // Test 2b: Akcja wywołuje skrypt Python (python_script lub pyscript)
    const actions = mainAlgo.action || mainAlgo.actions || [];
    const pythonAction = actions.find(a => a.service && (
      a.service.includes('python_script') ||
      a.service.includes('pyscript')
    ));
    if (pythonAction) {
      console.log(`[PASS] Algorytm wywołuje skrypt Python (${pythonAction.service})`);
      passed++;
    } else {
      console.log('[WARN] Algorytm nie wywołuje skryptu Python');
      warnings++;
    }
  } else {
    console.log('[FAIL] Brak głównej automatyzacji algorytmu');
    failed++;
  }

  // Test 3: Automatyzacja daily strategy (szukaj po alias)
  const dailyStrategy = automations.find(a => a.alias && a.alias.includes('Oblicz strategię dzienną'));
  if (dailyStrategy) {
    console.log('[PASS] Automatyzacja daily strategy istnieje');
    passed++;

    // Sprawdź trigger o 21:05
    const triggers = dailyStrategy.trigger || dailyStrategy.triggers || [];
    const timeTrigger = triggers.find(t => t.at === '21:05:00' || t.at === '21:05');
    if (timeTrigger) {
      console.log('[PASS] Daily strategy uruchamia się o 21:05');
      passed++;
    } else {
      console.log('[WARN] Daily strategy nie ma triggera o 21:05');
      warnings++;
    }
  } else {
    console.log('[WARN] Brak automatyzacji daily strategy');
    warnings++;
  }

  // Test 4: Automatyzacje bezpieczeństwa (temperature, SOC)
  const tempSafe = automations.find(a => a.alias && a.alias.toLowerCase().includes('temperatura'));
  if (tempSafe) {
    console.log('[PASS] Automatyzacja bezpieczeństwa temperatury istnieje');
    passed++;
  } else {
    console.log('[WARN] Brak automatyzacji bezpieczeństwa temperatury');
    warnings++;
  }

  // Test 5: Automatyzacje CWU
  const cwuAuto = automations.find(a => a.alias && a.alias.toLowerCase().includes('cwu'));
  if (cwuAuto) {
    console.log('[PASS] Automatyzacja CWU istnieje');
    passed++;
  } else {
    console.log('[WARN] Brak automatyzacji CWU');
    warnings++;
  }

  // Test 6: Każda automatyzacja ma mode (single/restart/queued/parallel)
  const withMode = automations.filter(a => a.mode);
  console.log(`[INFO] ${withMode.length}/${automations.length} automatyzacji ma zdefiniowany mode`);

  // Test 7: Sprawdź warunek wyjścia w automatyzacjach z pętlami
  const withRepeat = automations.filter(a => {
    const actions = a.action || a.actions || [];
    return actions.some(act => act.repeat);
  });
  withRepeat.forEach(a => {
    const actions = a.action || a.actions || [];
    const repeatAction = actions.find(act => act.repeat);
    // Warunek wyjścia: until (warunek), count (liczba powtórzeń), while (warunek)
    const hasExit = repeatAction && (
      repeatAction.repeat.until ||
      repeatAction.repeat.count ||
      repeatAction.repeat.while
    );
    if (hasExit) {
      const exitType = repeatAction.repeat.count ? `count: ${repeatAction.repeat.count}` :
                       repeatAction.repeat.until ? 'until' : 'while';
      console.log(`[PASS] Automatyzacja "${a.alias}" ma warunek wyjścia (${exitType})`);
      passed++;
    } else {
      console.log(`[WARN] Automatyzacja "${a.alias}" ma pętlę bez warunku wyjścia`);
      warnings++;
    }
  });

  console.log(`\n   Łącznie: ${automations.length} automatyzacji`);

} catch (e) {
  console.log(`[FAIL] Błąd parsowania: ${e.message}`);
  failed++;
}

console.log();

// ============================================
// TESTY automations_errors.yaml
// ============================================

console.log('## automations_errors.yaml');
console.log();

try {
  const content = fs.readFileSync(path.join(CONFIG_DIR, 'automations_errors.yaml'), 'utf8');
  const automations = yaml.load(content, { schema: HA_SCHEMA });

  // Test 1: Automatyzacja event log istnieje
  const eventLog = automations.find(a => a.alias && a.alias.toLowerCase().includes('event log'));
  if (eventLog) {
    console.log('[PASS] Automatyzacja Event Log istnieje');
    passed++;
  } else {
    console.log('[WARN] Brak automatyzacji Event Log');
    warnings++;
  }

  // Test 2: Automatyzacja telegram istnieje
  const telegram = automations.find(a => a.alias && a.alias.toLowerCase().includes('telegram'));
  if (telegram) {
    console.log('[PASS] Automatyzacja powiadomień Telegram istnieje');
    passed++;
  } else {
    console.log('[WARN] Brak automatyzacji Telegram');
    warnings++;
  }

  // Test 3: Automatyzacje mają warunki (conditions)
  const withConditions = automations.filter(a => {
    const cond = a.condition || a.conditions;
    return cond && (Array.isArray(cond) ? cond.length > 0 : true);
  });
  console.log(`[INFO] ${withConditions.length}/${automations.length} automatyzacji ma warunki (conditions)`);

  console.log(`\n   Łącznie: ${automations.length} automatyzacji błędów/powiadomień`);

} catch (e) {
  console.log(`[FAIL] Błąd parsowania: ${e.message}`);
  failed++;
}

console.log();

// ============================================
// TESTY automations.yaml (legacy TOU)
// ============================================

console.log('## automations.yaml (legacy TOU)');
console.log();

try {
  const content = fs.readFileSync(path.join(CONFIG_DIR, 'automations.yaml'), 'utf8');
  const automations = yaml.load(content, { schema: HA_SCHEMA });

  // Test 1: Automatyzacje TOU są wyłączone lub zintegrowane z nowym algorytmem
  const touAutomations = automations.filter(a => a.alias && a.alias.includes('TOU'));
  console.log(`[INFO] ${touAutomations.length} automatyzacji TOU (legacy)`);

  // Sprawdź czy są wyłączone
  const disabledTou = touAutomations.filter(a => a.enabled === false);
  if (disabledTou.length === touAutomations.length && touAutomations.length > 0) {
    console.log('[PASS] Wszystkie automatyzacje TOU są wyłączone (enabled: false)');
    passed++;
  } else if (touAutomations.length === 0) {
    console.log('[PASS] Brak starych automatyzacji TOU (zastąpione nowym algorytmem)');
    passed++;
  } else {
    console.log(`[WARN] ${touAutomations.length - disabledTou.length} automatyzacji TOU jest włączonych`);
    warnings++;
  }

  console.log(`\n   Łącznie: ${automations.length} automatyzacji w pliku legacy`);

} catch (e) {
  console.log(`[FAIL] Błąd parsowania: ${e.message}`);
  failed++;
}

console.log();
console.log('='.repeat(60));
console.log(`PODSUMOWANIE: ${passed} PASS, ${warnings} WARN, ${failed} FAIL`);
console.log('='.repeat(60));

if (failed > 0) {
  process.exit(1);
}
