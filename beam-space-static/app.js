/* Honest Copy Catalog, static replay.
 * Reads the saved Beam review (data/example_*.json, written by beam-space/scripts/make_cache.py)
 * plus the example catalog and evidence files, and renders them. Nothing is sent anywhere. */
(function () {
  'use strict';

  var REPO = 'https://github.com/kks0488/honest-copy/tree/beam-catalog/beam-space';
  var EXAMPLES = {
    en: { cache: 'data/example_en.json', catalog: 'data/catalog_en.csv',
          evidence: ['data/evidence_en/supplier_specs.txt', 'data/evidence_en/test_reports.txt'],
          sku: 'sku', copy: ['title', 'description'] },
    ko: { cache: 'data/example_ko.json', catalog: 'data/catalog_ko.csv',
          evidence: ['data/evidence_ko/supplier_specs_ko.txt', 'data/evidence_ko/test_reports_ko.txt'],
          sku: '상품코드', copy: ['상품명', '상세설명'] }
  };
  var LABELS = ['contradicted', 'no_evidence', 'supported', 'not_checked'];

  var T = {
    en: {
      title: 'Honest Copy Catalog',
      tagline: 'A second look at a whole shop catalog, with Beam',
      replay: 'This page replays a real Beam review of a fictional 30-product shop, generated on {when}. It makes no model calls and sends nothing anywhere.',
      full_app: 'The full app (upload your own CSV or XLSX, live Beam calls, English and Korean) runs from the repo:',
      disclaimer: 'A second look at wording, not legal or regulatory approval. Rules and the model can both miss things or be wrong.',
      loading: 'Loading the saved review...',
      load_error: 'Could not load the saved review files. If you opened this file directly, serve the folder over HTTP instead.',
      t_products: 'products read', t_flagged: 'products flagged', t_claims: 'claims flagged',
      t_contradicted: 'contradicted', t_no_evidence: 'no evidence', t_supported: 'supported',
      t_quotes: 'quotes matched exactly', t_rejected: 'model outputs rejected', t_calls: 'Beam calls',
      model: 'Model', generated: 'Generated', calls: 'Calls',
      by_label: 'By label', by_type: 'By type',
      tab_report: 'Report', tab_guard: 'Citation check', tab_input: 'What Beam read', tab_how: 'How it works',
      f_label: 'Label', f_type: 'Type', search: 'Search SKU, product or flagged text',
      dl_catalog: 'Corrected catalog CSV', dl_findings: 'Findings CSV',
      showing: 'Showing {n} of {total} flagged claims in {p} products.',
      none_match: 'No claims match these filters.',
      clean: 'No flags: {skus}',
      labels: { contradicted: 'Contradicted', no_evidence: 'No evidence', supported: 'Supported', not_checked: 'Not checked' },
      types: { contradiction: 'contradiction between products', spec_conflict: 'conflicts with your data', ranking: 'ranking', unsupported: 'unsupported',
               medical: 'medical claim', guarantee: 'guarantee', superlative: 'superlative', evidence: 'implied evidence' },
      type_group_beam: 'found by Beam', type_group_rules: 'found by rules',
      found: { rules: 'rules', beam: 'Beam' },
      found_by: 'found by {who}',
      no_cite: 'No line in the catalog or the documents was cited for this.',
      cite_dropped: 'Beam\u2019s citation did not match the files word for word, so it was dropped. See Citation check.',
      from_rule: 'Rule:', from_verifier: 'Verifier:', before: 'Before', after: 'After',
      related: 'Also see',
      fix: 'After the fix',
      keep: 'Kept as is (supported).',
      removed: 'Sentence removed.',
      needs_edit: 'Left for the seller to edit.',
      via_beam: 'rewritten by Beam', via_cleanup: 'flagged words removed',
      field_kept: '{col}: left as is, nothing usable would remain without the flagged words',
      guard_intro: 'Every quote Beam gives is compared with your files, character by character, in code. A quote that is not there is thrown away, a claim cannot cite itself, and a label that loses all its citations is lowered to "no evidence". Rewrites that break a rule are rejected too. Everything thrown away is listed here.',
      g_checked: 'quotes Beam cited', g_accepted: 'matched your files exactly', g_rejected: 'outputs rejected',
      g_steps: 'Beam passes in this run',
      g_cols: ['Pass', 'Item', 'What Beam said', 'Why it was rejected'],
      g_none: 'Nothing was rejected in this run.',
      g_file_says: 'Your file says:',
      step_names: { audit: 'Whole-catalog pass', verify: 'Verifier pass', rewrite: 'Rewrite pass' },
      input_intro: 'This is everything Beam read in the whole-catalog pass: the full catalog, one product per row, and every line of the seller’s evidence documents. Flagged words are highlighted.',
      evidence_docs: 'Evidence documents',
      footer: 'Example shops and documents are fictional sample data. Built on the Honest Copy phrase rules. Model: Beam 1.0 (Apache 2.0).',
      csv_cols: ['SKU', 'Column', 'Flagged text', 'Found by', 'Reason', 'Cited evidence', 'Label', 'Sentence after the fix'],
      csv_none: 'none found', csv_keep: 'keep as is', csv_edit: 'needs your edit', csv_removed: 'sentence removed'
    },
    ko: {
      title: 'Honest Copy Catalog',
      tagline: '가게 상품 목록 전체를 Beam으로 한 번 더 살펴봅니다',
      replay: '가상의 30개 상품 가게를 Beam으로 실제 검토한 결과를 다시 보여 드립니다. 생성 시각: {when}. 이 페이지는 모델을 호출하지 않고 아무것도 보내지 않습니다.',
      full_app: '내 CSV나 XLSX를 올려 Beam으로 직접 검토하는 전체 앱은 저장소에서 실행합니다:',
      disclaimer: '문구를 한 번 더 살펴보는 참고용이며 법률 검토나 심의 통과가 아닙니다. 규칙과 모델 모두 놓치거나 틀릴 수 있습니다.',
      loading: '저장된 검토 결과를 불러오는 중...',
      load_error: '저장된 검토 파일을 불러오지 못했습니다. 파일을 직접 열었다면 폴더를 HTTP로 열어 주세요.',
      t_products: '읽은 상품', t_flagged: '표시된 상품', t_claims: '표시된 주장',
      t_contradicted: '자료와 충돌', t_no_evidence: '근거 없음', t_supported: '근거 있음',
      t_quotes: '글자 그대로 일치한 인용', t_rejected: '버린 모델 출력', t_calls: 'Beam 호출',
      model: '모델', generated: '생성', calls: '호출',
      by_label: '판정별', by_type: '유형별',
      tab_report: '검토 결과', tab_guard: '인용 확인', tab_input: 'Beam이 읽은 자료', tab_how: '작동 방식',
      f_label: '판정', f_type: '유형', search: '상품코드, 상품명, 표시된 문구 검색',
      dl_catalog: '고친 상품 목록 CSV', dl_findings: '검토 항목 CSV',
      showing: '상품 {p}개, 표시된 주장 {total}개 중 {n}개를 보여 드립니다.',
      none_match: '조건에 맞는 주장이 없습니다.',
      clean: '표시 없음: {skus}',
      labels: { contradicted: '자료와 충돌', no_evidence: '근거 없음', supported: '근거 있음', not_checked: '확인 전' },
      types: { contradiction: '상품끼리 충돌', spec_conflict: '내 자료와 다름', ranking: '순위 주장', unsupported: '근거 없는 사실',
               medical: '의료 효능', guarantee: '절대 보장', superlative: '최상급 표현', evidence: '근거 암시' },
      type_group_beam: 'Beam이 찾음', type_group_rules: '규칙이 찾음',
      found: { rules: '규칙', beam: 'Beam' },
      found_by: '찾은 곳: {who}',
      no_cite: '이 주장에 대해 인용된 상품 목록 셀이나 문서 줄이 없습니다.',
      cite_dropped: 'Beam의 인용이 파일과 글자 그대로 맞지 않아 버렸습니다. 인용 확인 탭을 보세요.',
      from_rule: '규칙:', from_verifier: '근거 확인:', before: '전', after: '후',
      related: '함께 볼 줄',
      fix: '고친 뒤',
      keep: '그대로 둠 (근거 있음).',
      removed: '문장을 뺐습니다.',
      needs_edit: '직접 고쳐야 합니다.',
      via_beam: 'Beam이 고침', via_cleanup: '표시된 부분만 삭제',
      field_kept: '{col}: 표시된 부분을 지우면 쓸 만한 문장이 남지 않아 그대로 둠',
      guard_intro: 'Beam이 인용한 문장은 코드에서 내 파일과 한 글자씩 비교합니다. 파일에 없는 인용은 버리고, 주장이 자기 자신을 근거로 삼을 수 없으며, 인용이 모두 버려진 판정은 "근거 없음"으로 낮춥니다. 규칙을 어긴 고쳐 쓰기도 버립니다. 버린 것은 모두 여기에 남깁니다.',
      g_checked: 'Beam이 인용한 문장', g_accepted: '내 파일과 글자 그대로 일치', g_rejected: '버린 출력',
      g_steps: '이번 검토의 Beam 단계',
      g_cols: ['단계', '항목', 'Beam의 출력', '버린 이유'],
      g_none: '이번 검토에서 버린 출력은 없습니다.',
      g_file_says: '실제 파일 내용:',
      step_names: { audit: '목록 전체 검토', verify: '근거 확인', rewrite: '고쳐 쓰기' },
      input_intro: 'Beam이 목록 전체 검토에서 읽은 자료 전부입니다. 상품 목록 전체(한 줄에 상품 하나)와 판매자 근거 문서의 모든 줄입니다. 표시된 문구는 강조했습니다.',
      evidence_docs: '근거 문서',
      footer: '예시 가게와 문서는 가상의 자료입니다. Honest Copy 문구 규칙을 바탕으로 만들었습니다. 모델: Beam 1.0 (Apache 2.0).',
      csv_cols: ['상품코드', '열', '표시된 문구', '찾은 곳', '이유', '인용 근거', '판정', '고친 뒤 문장'],
      csv_none: '찾지 못함', csv_keep: '그대로 두기', csv_edit: '직접 수정 필요', csv_removed: '문장 삭제'
    }
  };
  var STEP_TEXT = {
    en: [
      ['Whole catalog in one long-context pass',
       'All 30 products go to Beam in a single request, one source per line (<code>EN-003/material :: 100% cotton, 380 GSM</code>), followed by every line of the evidence documents (<code>supplier_specs.txt#L5 :: ...</code>). With a 1M-token context window Beam sees every product next to every other product, which is what makes cross-product checks possible: the same towel at 500 GSM in one row and 380 GSM in another, a "same formula" sun stick with a different SPF, several products all claiming first place. Splitting the catalog into chunks would hide exactly these problems. Local phrase rules (medical promises, guarantees, rankings, implied evidence) run first with no model call, and their hits join the list.'],
      ['Verifier pass with an exact-quote check in code',
       'Every flagged claim goes back to Beam with the whole catalog again. For each one Beam must label it supported, contradicted or no evidence, and quote the catalog cell or document line it relies on. The app then checks every quote by exact substring match against the named source. A quote that is not in the input is thrown away, a claim may not cite itself, and a label whose citations all fail is lowered to no evidence. The Citation check tab lists everything that was rejected.'],
      ['Whole-field rewrite with code guards and a fallback',
       'Every affected product goes into one batched request. Beam rewrites each title or description as a whole, fixing all its flagged claims at once, in the seller’s tone and language, using only facts from that product’s row or the verified evidence. In code: every sentence without a flag must come back word for word; no new numbers; same language; nothing that still trips a rule; no bare one or two word fragments unless it is a fact from the seller’s data (54 cm to 58 cm, Portugal to Vietnam). When a check fails, the flagged words are removed cleanly instead, or the sentence is dropped, and the field is never emptied.'],
      ['At most three Beam calls per catalog',
       'One whole-catalog pass, one verifier pass, one batched rewrite pass. The full app also has a daily call cap and an input size limit, and still runs the local rules when Beam is not available.']
    ],
    ko: [
      ['목록 전체를 한 번에 읽는 긴 문맥 검토',
       '상품 30개를 한 번의 요청으로 Beam에 보냅니다. 한 줄에 자료 하나씩(<code>KO-003/소재 :: 면 100%, 380g/㎡</code>), 이어서 근거 문서의 모든 줄(<code>supplier_specs_ko.txt#L5 :: ...</code>)을 넣습니다. Beam은 100만 토큰 문맥 덕분에 모든 상품을 서로 나란히 놓고 볼 수 있어, 상품끼리 맞지 않는 설명을 찾을 수 있습니다. 한 줄에서는 500g/㎡, 다른 줄에서는 380g/㎡인 같은 타월, "같은 제형"이라면서 SPF가 다른 선스틱, 여러 상품의 1위 주장 같은 것들입니다. 목록을 나눠 보내면 바로 이런 문제가 가려집니다. 그 전에 로컬 문구 규칙(의료 효능, 절대 보장, 순위, 근거 암시)이 모델 호출 없이 먼저 돌고, 찾은 표현이 목록에 합쳐집니다.'],
      ['코드로 인용을 그대로 대조하는 근거 확인',
       '표시된 주장을 목록 전체와 함께 다시 Beam에 보냅니다. Beam은 주장마다 근거 있음, 자료와 충돌, 근거 없음 중 하나로 판정하고, 근거가 되는 셀이나 문서 줄을 그대로 인용해야 합니다. 앱은 그 인용이 지목한 줄에 글자 그대로 있는지 코드로 확인합니다. 입력에 없는 인용은 버리고, 주장이 자기 자신을 근거로 삼을 수 없으며, 인용이 모두 버려진 판정은 근거 없음으로 낮춥니다. 버린 것은 인용 확인 탭에 모두 나옵니다.'],
      ['필드 전체를 고쳐 쓰고 코드로 검사, 실패하면 안전하게 되돌림',
       '고칠 상품을 모두 한 번의 요청에 묶습니다. Beam은 상품명이나 상세설명을 통째로, 표시된 주장을 한 번에 고쳐 판매자의 말투와 언어로 다시 씁니다. 그 상품의 자료나 확인된 근거에 있는 사실만 씁니다. 코드에서는 표시가 없는 문장이 한 글자도 바뀌지 않았는지, 새 숫자가 없는지, 언어가 같은지, 여전히 규칙에 걸리지 않는지, 한두 단어짜리 토막 문구가 아닌지(판매자 자료의 사실로 바꾼 경우는 예외, 예: 54cm를 58cm로, 포르투갈을 베트남으로) 확인합니다. 검사를 통과하지 못하면 표시된 부분만 깔끔하게 지우거나 그 문장을 빼고, 필드를 비우지는 않습니다.'],
      ['목록 하나에 Beam 호출은 최대 세 번',
       '목록 전체 검토 한 번, 근거 확인 한 번, 고쳐 쓰기 한 번입니다. 전체 앱에는 하루 호출 한도와 입력 크기 제한이 있고, Beam을 쓸 수 없을 때도 로컬 규칙은 돌아갑니다.']
    ]
  };
  var RUN_TITLE = { en: 'Run the full app', ko: '전체 앱 실행' };
  var RUN_CMDS = 'git clone -b beam-catalog https://github.com/kks0488/honest-copy.git\ncd honest-copy/beam-space && pip install -r requirements.txt\nHF_TOKEN=your_token python app.py';
  var RUN_NOTE = {
    en: 'Without a token the app still runs the local rules and shows this saved review for the examples.',
    ko: '토큰이 없어도 로컬 규칙은 돌아가고, 예시에는 이 저장된 결과를 보여 줍니다.'
  };

  var state = { lang: 'en', tab: 'report', data: {}, labels: new Set(LABELS), types: null, q: '' };

  // ------------------------------------------------------------------ helpers
  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function t(key, vars) {
    var v = (T[state.lang] && T[state.lang][key] !== undefined) ? T[state.lang][key] : T.en[key];
    if (typeof v === 'string' && vars) {
      v = v.replace(/\{(\w+)\}/g, function (_, k) { return vars[k] !== undefined ? vars[k] : ''; });
    }
    return v;
  }
  function fmtWhen(iso) {
    if (!iso) return '?';
    var m = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/.exec(iso);
    return m ? m[1] + ' ' + m[2] + ' UTC' : iso;
  }
  function highlight(text, quote) {
    if (!quote) return esc(text);
    var i = text.indexOf(quote);
    if (i < 0) return esc(text);
    return esc(text.slice(0, i)) + '<mark>' + esc(quote) + '</mark>' + esc(text.slice(i + quote.length));
  }
  function highlightMany(text, quotes) {
    var spans = [];
    quotes.forEach(function (q) {
      var i = q ? text.indexOf(q) : -1;
      if (i >= 0) spans.push([i, i + q.length]);
    });
    spans.sort(function (a, b) { return a[0] - b[0]; });
    var out = '', pos = 0;
    spans.forEach(function (s) {
      if (s[0] < pos) return;
      out += esc(text.slice(pos, s[0])) + '<mark>' + esc(text.slice(s[0], s[1])) + '</mark>';
      pos = s[1];
    });
    return out + esc(text.slice(pos));
  }

  // CSV parsing (RFC 4180, quoted fields, CRLF)
  function parseCSV(text) {
    text = text.replace(/^﻿/, '');
    var rows = [], row = [], cell = '', i = 0, q = false;
    while (i < text.length) {
      var c = text[i];
      if (q) {
        if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else { q = false; } }
        else cell += c;
      } else if (c === '"') { q = true; }
      else if (c === ',') { row.push(cell); cell = ''; }
      else if (c === '\n' || c === '\r') {
        if (c === '\r' && text[i + 1] === '\n') i++;
        row.push(cell); rows.push(row); row = []; cell = '';
      } else cell += c;
      i++;
    }
    if (cell !== '' || row.length) { row.push(cell); rows.push(row); }
    return rows.filter(function (r) { return r.some(function (c) { return c.trim() !== ''; }); });
  }
  function cleanCell(v) { return String(v || '').replace(/\s*[\r\n]+\s*/g, ' ').trim(); }
  function csvLine(cells) {
    return cells.map(function (c) {
      c = String(c == null ? '' : c);
      return /[",\r\n]/.test(c) ? '"' + c.replace(/"/g, '""') + '"' : c;
    }).join(',');
  }
  function download(name, text) {
    var blob = new Blob(['﻿' + text], { type: 'text/csv;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }

  // word diff (LCS over words, spaces and punctuation marks)
  function diffWords(before, after) {
    var tok = /\s+|[^\s.,!?;:]+|[.,!?;:]/g;
    var a = before.match(tok) || [], b = after.match(tok) || [];
    var n = a.length, m = b.length, dp = [];
    for (var i = 0; i <= n; i++) { dp.push(new Array(m + 1).fill(0)); }
    for (i = n - 1; i >= 0; i--) for (var j = m - 1; j >= 0; j--)
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    var ops = [];
    function push(op, s) {
      if (ops.length && ops[ops.length - 1][0] === op) ops[ops.length - 1][1] += s; else ops.push([op, s]);
    }
    i = 0; j = 0;
    while (i < n && j < m) {
      if (a[i] === b[j]) { push('same', a[i]); i++; j++; }
      else if (dp[i + 1][j] >= dp[i][j + 1]) { push('del', a[i]); i++; }
      else { push('ins', b[j]); j++; }
    }
    while (i < n) push('del', a[i++]);
    while (j < m) push('ins', b[j++]);
    return ops;
  }
  // one side of the diff: the "before" text with removals marked, or the "after" text with additions marked
  function diffSide(ops, side) {
    var skip = side === 'before' ? 'ins' : 'del', tag = side === 'before' ? 'del' : 'ins';
    var list = [];
    ops.filter(function (o) { return o[0] !== skip; }).forEach(function (o) {
      var last = list[list.length - 1];
      if (last && last[0] === o[0]) { last[1] += o[1]; return; }
      // a lone space between two changed runs belongs to the change, so it reads as one phrase
      if (o[0] === tag && last && last[0] === 'same' && !last[1].trim() && list.length > 1 && list[list.length - 2][0] === tag) {
        list.pop(); list[list.length - 1][1] += last[1] + o[1]; return;
      }
      list.push([o[0], o[1]]);
    });
    return list.map(function (o) {
      if (o[0] === 'same') return esc(o[1]);
      var lead = (o[1].match(/^\s*/) || [''])[0], trail = (o[1].match(/\s*$/) || [''])[0];
      var core = o[1].trim();
      return core ? esc(lead) + '<' + tag + '>' + esc(core) + '</' + tag + '>' + esc(trail) : esc(o[1]);
    }).join('');
  }
  function diffText(before, after) {
    var out = diffWords(before, after).filter(function (o) { return o[1].trim() || o[0] === 'same'; }).map(function (o) {
      if (o[0] === 'same') return o[1];
      return o[0] === 'del' ? ' [-' + o[1].trim() + '-] ' : ' {+' + o[1].trim() + '+} ';
    }).join('');
    return out.replace(/ {2,}/g, ' ').trim();
  }

  // ------------------------------------------------------------------ data
  function load(key) {
    if (state.data[key]) return Promise.resolve(state.data[key]);
    var ex = EXAMPLES[key];
    var getText = function (u) { return fetch(u).then(function (r) { if (!r.ok) throw new Error(u); return r.text(); }); };
    return Promise.all([getText(ex.cache), getText(ex.catalog)].concat(ex.evidence.map(getText))).then(function (parts) {
      var cache = JSON.parse(parts[0]);
      var rows = parseCSV(parts[1]);
      var headers = rows[0].map(cleanCell);
      var products = rows.slice(1).map(function (r) {
        var cells = {};
        headers.forEach(function (h, i) { cells[h] = cleanCell(r[i]); });
        return { sku: cells[ex.sku], cells: cells };
      });
      var sources = {};
      products.forEach(function (p) { headers.forEach(function (h) { if (h !== ex.sku && p.cells[h]) sources[p.sku + '/' + h] = p.cells[h]; }); });
      var docs = ex.evidence.map(function (path, k) {
        var name = path.split('/').pop();
        var lines = [];
        parts[2 + k].split(/\r?\n/).forEach(function (line, i) {
          var s = line.replace(/[ \t ]+/g, ' ').trim();
          if (s) { lines.push([i + 1, s]); sources[name + '#L' + (i + 1)] = s; }
        });
        return { name: name, lines: lines };
      });
      var d = { key: key, ex: ex, cache: cache, result: cache.result || {}, headers: headers, products: products, docs: docs, sources: sources };
      state.data[key] = d;
      return d;
    });
  }

  function typesOf(c) {
    var out = (c.beam_types || []).slice();
    if (c.category) out.push(c.category);
    return out;
  }
  function counts(d) {
    var claims = d.result.claims || [];
    var lab = {}, typ = {};
    LABELS.forEach(function (l) { lab[l] = 0; });
    claims.forEach(function (c) {
      lab[c.label] = (lab[c.label] || 0) + 1;
      typesOf(c).forEach(function (x) { typ[x] = (typ[x] || 0) + 1; });
    });
    var skus = {};
    claims.forEach(function (c) { skus[c.sku] = 1; });
    return { claims: claims.length, labels: lab, types: typ, flagged: Object.keys(skus).length };
  }
  function wasLowered(c) {
    var d = state.data[state.lang];
    return !!d && (d.result.guard || []).some(function (g) { return g.item === c.id && /label lowered/.test(g.reason); });
  }
  function reasonParts(c) {
    var main = c.beam_reason || '';
    var rule = state.lang === 'ko' && c.rule_reason_ko ? c.rule_reason_ko : c.rule_reason;
    var note = c.label_note && c.label_note !== main && c.label_note !== rule ? c.label_note : '';
    if (wasLowered(c)) note = t('cite_dropped');  // the app's own note, shown in the page language
    // house style for explanations: a comma instead of a middle dot (quotes and citations are never touched)
    var tidy = function (x) { return (x || '').replace(/\s*\u00b7\s*/g, ', '); };
    return { main: tidy(main), rule: rule || '', note: tidy(note) };
  }
  function fixText(c, forCsv) {
    if (c.label === 'supported') return forCsv ? t('csv_keep') : t('keep');
    if (c.rewrite_from !== 'beam' && c.rewrite_from !== 'cleanup') return forCsv ? t('csv_edit') : t('needs_edit');
    var how = c.rewrite_from === 'beam' ? t('via_beam') : t('via_cleanup');
    var txt = c.rewrite || (forCsv ? t('csv_removed') : t('removed'));
    return forCsv ? txt + ' (' + how + ')' : { text: txt, how: how, removed: !c.rewrite };
  }

  // ------------------------------------------------------------------ render
  function renderStatic() {
    document.documentElement.lang = state.lang;
    document.querySelectorAll('[data-t]').forEach(function (el) { el.textContent = t(el.getAttribute('data-t')); });
    $('search').placeholder = t('search');
    $('search').setAttribute('aria-label', t('search'));
    document.querySelectorAll('.switch button').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.getAttribute('data-lang') === state.lang));
    });
  }

  function renderReplay(d) {
    var when = fmtWhen(d.cache.generated_at);
    $('replay').innerHTML =
      '<p>' + esc(t('replay', { when: when })) + '</p>' +
      '<p>' + esc(t('full_app')) + ' <a href="' + REPO + '" target="_blank" rel="noopener">github.com/kks0488/honest-copy/tree/beam-catalog/beam-space</a></p>' +
      '<p class="disclaimer">' + esc(t('disclaimer')) + '</p>';
  }

  function tile(n, label, cls) {
    return '<div class="tile ' + (cls || '') + '"><div class="n">' + esc(n) + '</div><div class="l">' + esc(label) + '</div></div>';
  }
  function renderSummary(d) {
    var k = counts(d), r = d.result;
    var types = T[state.lang].types;
    var beamTypes = ['contradiction', 'spec_conflict', 'ranking', 'unsupported'];
    var ruleTypes = ['medical', 'guarantee', 'superlative', 'evidence'];
    var chipList = function (list) {
      return list.filter(function (x) { return k.types[x]; }).map(function (x) {
        return '<span class="chip">' + esc(types[x]) + ' <b>' + k.types[x] + '</b></span>';
      }).join('');
    };
    $('summary').innerHTML =
      '<div class="tiles">' +
        tile(d.products.length, t('t_products')) +
        tile(k.flagged, t('t_flagged')) +
        tile(k.claims, t('t_claims')) +
        tile(k.labels.contradicted, t('t_contradicted'), 'bad') +
        tile(k.labels.no_evidence, t('t_no_evidence'), 'warn') +
        tile((r.quotes_accepted || 0) + ' / ' + (r.quotes_checked || 0), t('t_quotes'), 'ok') +
      '</div>' +
      '<div class="bytype">' +
        '<div><h3>' + esc(t('by_type')) + ', ' + esc(t('type_group_beam')) + '</h3><div class="chips">' + chipList(beamTypes) + '</div></div>' +
        '<div><h3>' + esc(t('by_type')) + ', ' + esc(t('type_group_rules')) + '</h3><div class="chips">' + chipList(ruleTypes) + '</div></div>' +
      '</div>' +
      '<div class="meta">' +
        '<span>' + esc(t('model')) + ': <b>' + esc(d.cache.model || r.model) + '</b></span>' +
        '<span>' + esc(t('generated')) + ': <b>' + esc(fmtWhen(d.cache.generated_at)) + '</b></span>' +
        '<span>' + esc(t('calls')) + ': <b>' + esc(r.calls_made) + '</b></span>' +
        '<span>' + esc(t('t_rejected')) + ': <b>' + esc((r.guard || []).length) + '</b></span>' +
        '<span>' + esc(t('t_supported')) + ': <b>' + esc(k.labels.supported) + '</b></span>' +
      '</div>';
    var badge = (r.guard || []).length;
    var gt = document.querySelector('[data-tab="guard"]');
    gt.innerHTML = esc(t('tab_guard')) + (badge ? '<span class="badge">' + badge + '</span>' : '');
  }

  function renderFilters(d) {
    var k = counts(d);
    if (!state.types) state.types = new Set(Object.keys(k.types));
    var labels = T[state.lang].labels, types = T[state.lang].types;
    var lrow = LABELS.filter(function (l) { return k.labels[l]; }).map(function (l) {
      return '<button type="button" class="fbtn" data-flabel="' + l + '" aria-pressed="' + state.labels.has(l) + '">' +
        esc(labels[l]) + '<span class="k">' + k.labels[l] + '</span></button>';
    }).join('');
    var trow = Object.keys(types).filter(function (x) { return k.types[x]; }).map(function (x) {
      return '<button type="button" class="fbtn" data-ftype="' + x + '" aria-pressed="' + state.types.has(x) + '">' +
        esc(types[x]) + '<span class="k">' + k.types[x] + '</span></button>';
    }).join('');
    $('filters').innerHTML =
      '<div class="filter-row"><span class="lab">' + esc(t('f_label')) + '</span>' + lrow + '</div>' +
      '<div class="filter-row"><span class="lab">' + esc(t('f_type')) + '</span>' + trow + '</div>';
  }

  function claimPasses(c) {
    if (!state.labels.has(c.label)) return false;
    if (!typesOf(c).some(function (x) { return state.types.has(x); })) return false;
    return true;
  }

  function renderClaim(d, c) {
    var labels = T[state.lang].labels, types = T[state.lang].types, found = T[state.lang].found;
    var rp = reasonParts(c);
    var who = (c.origin || []).map(function (o) { return found[o] || o; }).join(' + ');
    var head = '<div class="claim-head"><span class="quote"><mark>' + esc(c.quote) + '</mark></span>' +
      '<span class="pill ' + esc(c.label) + '">' + esc(labels[c.label] || c.label) + '</span>' +
      typesOf(c).map(function (x) { return '<span class="tag">' + esc(types[x] || x) + '</span>'; }).join('') +
      '<span class="where">' + esc(c.column) + ', ' + esc(t('found_by', { who: who })) + '</span></div>';
    var reason = '<p class="reason">' + esc(rp.main || rp.rule) +
      (rp.main && rp.rule ? '<span class="rule"><b>' + esc(t('from_rule')) + '</b> ' + esc(rp.rule) + '</span>' : '') +
      (rp.note ? '<span class="rule"><b>' + esc(t('from_verifier')) + '</b> ' + esc(rp.note) + '</span>' : '') + '</p>';
    var cites = '';
    if (c.citations && c.citations.length) {
      cites = '<div class="cites">' + c.citations.map(function (x) {
        var line = d.sources[x.source];
        return '<div class="cite ' + esc(c.label) + '"><div class="src">' + esc(x.source) + '</div>' +
          '<div class="line">' + (line ? highlight(line, x.quote) : '<mark>' + esc(x.quote) + '</mark>') + '</div></div>';
      }).join('') + '</div>';
    } else if (c.label !== 'not_checked') {
      if (!wasLowered(c)) cites = '<p class="nocite">' + esc(t('no_cite')) + '</p>';
    }
    var cited = {};
    (c.citations || []).forEach(function (x) { cited[x.source] = 1; });
    var rel = (c.related || []).filter(function (r) { return !cited[r]; });
    var related = rel.length ? '<p class="related">' + esc(t('related')) + ': ' + rel.map(function (r) { return '<code>' + esc(r) + '</code>'; }).join(', ') + '</p>' : '';
    // the rewritten text is shown once per field above; here only what the field view cannot say
    var f = fixText(c, false), fix = '';
    if (typeof f === 'string') fix = '<div class="fix"><span class="k">' + esc(t('fix')) + '</span>' + esc(f) + '</div>';
    else if (f.removed) fix = '<div class="fix"><span class="k">' + esc(t('fix')) + '</span><em>' + esc(f.text) + '</em></div>';
    return '<li class="claim" id="claim-' + esc(c.id) + '">' + head + reason + cites + related + fix + '</li>';
  }

  function renderCards(d) {
    var claims = d.result.claims || [];
    var q = state.q.trim().toLowerCase();
    var bySku = {};
    claims.forEach(function (c) { (bySku[c.sku] = bySku[c.sku] || []).push(c); });
    var shown = 0, prodShown = 0, html = '', clean = [];
    var titleCol = d.ex.copy[0];
    d.products.forEach(function (p) {
      var list = bySku[p.sku];
      if (!list) { clean.push(p.sku); return; }
      var title = p.cells[titleCol] || '';
      var match = !q || p.sku.toLowerCase().indexOf(q) >= 0 || title.toLowerCase().indexOf(q) >= 0 ||
        list.some(function (c) { return c.quote.toLowerCase().indexOf(q) >= 0; });
      var visible = match ? list.filter(claimPasses) : [];
      if (!visible.length) return;
      shown += visible.length; prodShown++;
      var fields = (d.result.field_rewrites || []).filter(function (f) { return f.sku === p.sku; }).map(function (f) {
        if (f.after === f.before) {
          return '<div class="field"><div class="field-label">' + esc(t('field_kept', { col: f.column })) + '</div><p class="diff">' + esc(f.before) + '</p></div>';
        }
        var hows = {};
        (f.gaps || []).forEach(function (g) { hows[g.source === 'beam' ? t('via_beam') : t('via_cleanup')] = 1; });
        var ops = diffWords(f.before, f.after);
        return '<div class="field"><div class="field-label"><span>' + esc(f.column) + '</span>' +
          Object.keys(hows).map(function (h) { return '<span class="tag">' + esc(h) + '</span>'; }).join('') + '</div>' +
          '<div class="ba"><span class="k">' + esc(t('before')) + '</span><p class="diff">' + diffSide(ops, 'before') + '</p></div>' +
          '<div class="ba"><span class="k">' + esc(t('after')) + '</span><p class="diff">' + diffSide(ops, 'after') + '</p></div></div>';
      }).join('');
      html += '<article class="card" id="p-' + esc(p.sku) + '"><div class="card-head"><span class="sku">' + esc(p.sku) + '</span>' +
        '<h3>' + esc(title) + '</h3><span class="n">' + visible.length + ' / ' + list.length + '</span></div>' +
        fields + '<ul class="claims">' + visible.map(function (c) { return renderClaim(d, c); }).join('') + '</ul></article>';
    });
    $('cards').innerHTML = html || '<div class="empty">' + esc(t('none_match')) + '</div>';
    $('count').textContent = t('showing', { n: shown, total: claims.length, p: prodShown });
    $('clean').textContent = clean.length ? t('clean', { skus: clean.join(', ') }) : '';
  }

  function renderGuard(d) {
    var r = d.result, guard = r.guard || [];
    var names = T[state.lang].step_names, cols = t('g_cols');
    var steps = (r.steps || []).map(function (s) {
      return '<li><span class="' + (s.ok ? 'ok' : 'fail') + '">' + (s.ok ? '✓' : '✕') + '</span><b>' + esc(names[s.step] || s.step) + '</b>: ' + esc(s.detail) + '</li>';
    }).join('');
    var rows = guard.map(function (g) {
      var item = /^C\d+$/.test(g.item) ? '<a href="#claim-' + esc(g.item) + '" data-goto="' + esc(g.item) + '">' + esc(g.item) + '</a>' : esc(g.item);
      var said = '<code>' + esc(g.text) + '</code>';
      var m = /^(\S+): ([\s\S]*)$/.exec(g.text || '');
      if (m && d.sources[m[1]] !== undefined) {
        said = '<div class="muted small">' + esc(m[1]) + '</div><code>' + esc(m[2]) + '</code>' +
          '<div class="muted small" style="margin-top:4px">' + esc(t('g_file_says')) + ' <code>' + esc(d.sources[m[1]]) + '</code></div>';
      }
      return '<tr><td>' + esc(names[g.step] || g.step) + '</td><td>' + item + '</td><td>' + said + '</td><td>' + esc(g.reason) + '</td></tr>';
    }).join('');
    $('panel-guard').innerHTML =
      '<p class="section-intro">' + esc(t('guard_intro')) + '</p>' +
      '<div class="guard-sum">' + tile(r.quotes_checked || 0, t('g_checked')) + tile(r.quotes_accepted || 0, t('g_accepted'), 'ok') + tile(guard.length, t('g_rejected'), guard.length ? 'bad' : '') + '</div>' +
      '<h3 class="small muted" style="margin:0 0 6px">' + esc(t('g_steps')) + '</h3><ul class="steps">' + steps + '</ul>' +
      (rows ? '<div class="tbl-wrap"><table><thead><tr>' + cols.map(function (h) { return '<th>' + esc(h) + '</th>'; }).join('') +
        '</tr></thead><tbody>' + rows + '</tbody></table></div>' : '<div class="empty">' + esc(t('g_none')) + '</div>');
  }

  function renderInput(d) {
    var claims = d.result.claims || [];
    var quotesBySource = {};
    claims.forEach(function (c) { (quotesBySource[c.source] = quotesBySource[c.source] || []).push(c.quote); });
    var head = '<tr>' + d.headers.map(function (h) { return '<th>' + esc(h) + '</th>'; }).join('') + '</tr>';
    var body = d.products.map(function (p) {
      return '<tr>' + d.headers.map(function (h) {
        var v = p.cells[h] || '';
        var cls = h === d.ex.sku ? 'sku' : (d.ex.copy.indexOf(h) >= 0 ? 'copy' : '');
        var qs = quotesBySource[p.sku + '/' + h];
        return '<td class="' + cls + '">' + (qs ? highlightMany(v, qs) : esc(v)) + '</td>';
      }).join('') + '</tr>';
    }).join('');
    var docs = d.docs.map(function (doc) {
      return '<div class="doc"><h3><code>' + esc(doc.name) + '</code></h3><ol>' + doc.lines.map(function (l) {
        return '<li><span class="ln">#L' + l[0] + '</span><span>' + esc(l[1]) + '</span></li>';
      }).join('') + '</ol></div>';
    }).join('');
    $('panel-input').innerHTML = '<p class="section-intro">' + esc(t('input_intro')) + '</p>' +
      '<div class="tbl-wrap"><table class="catalog"><thead>' + head + '</thead><tbody>' + body + '</tbody></table></div>' +
      '<h2 class="small muted" style="margin:18px 0 0">' + esc(t('evidence_docs')) + '</h2>' + docs;
  }

  function renderHow() {
    var steps = STEP_TEXT[state.lang].map(function (s, i) {
      return '<div class="step"><h3><span class="num">' + (i + 1) + '</span>' + esc(s[0]) + '</h3><p>' + s[1] + '</p></div>';
    }).join('');
    $('panel-how').innerHTML = '<div class="how">' + steps +
      '<div class="step"><h3>' + esc(RUN_TITLE[state.lang]) + '</h3>' +
      '<p><a href="' + REPO + '" target="_blank" rel="noopener">' + REPO.replace('https://', '') + '</a></p>' +
      '<pre>' + esc(RUN_CMDS) + '</pre><p class="muted small">' + esc(RUN_NOTE[state.lang]) + '</p></div></div>';
  }

  // ------------------------------------------------------------------ CSV exports
  function correctedCSV(d) {
    var labels = {};
    (d.result.claims || []).forEach(function (c) { labels[c.id] = c.label.replace('_', ' '); });
    var newCells = {}, notes = {}, diffs = {};
    var rows = {};
    d.products.forEach(function (p) { rows[p.sku] = p; });
    (d.result.field_rewrites || []).forEach(function (f) {
      var p = rows[f.sku];
      if (!p || p.cells[f.column] !== f.before) return;
      (f.gaps || []).forEach(function (g) {
        var flags = g.claim_ids.map(function (id) { return id + ' ' + (labels[id] || ''); }).join(', ');
        var how = { beam: 'rewritten', cleanup: 'flagged words removed', kept: 'needs your edit' }[g.source];
        (notes[f.sku] = notes[f.sku] || []).push(f.column + ': ' + flags + ' (' + how + ')');
      });
      if (f.after !== f.before) {
        (newCells[f.sku] = newCells[f.sku] || {})[f.column] = f.after;
        (diffs[f.sku] = diffs[f.sku] || []).push(f.column + ': ' + diffText(f.before, f.after));
      }
    });
    var head = d.headers.concat(['review_note', 'changes'], d.ex.copy.map(function (h) { return h + ' (before)'; }));
    var lines = [csvLine(head)];
    d.products.forEach(function (p) {
      var nc = newCells[p.sku] || {};
      lines.push(csvLine(d.headers.map(function (h) { return nc[h] !== undefined ? nc[h] : p.cells[h]; })
        .concat([(notes[p.sku] || []).join(' | '), (diffs[p.sku] || []).join(' | ')],
                d.ex.copy.map(function (h) { return nc[h] !== undefined ? p.cells[h] : ''; }))));
    });
    return lines.join('\r\n') + '\r\n';
  }
  function findingsCSV(d) {
    var labels = T[state.lang].labels, found = T[state.lang].found;
    var lines = [csvLine(t('csv_cols'))];
    (d.result.claims || []).forEach(function (c) {
      var rp = reasonParts(c);
      var ev = (c.citations || []).length ? c.citations.map(function (x) { return '[' + x.source + '] "' + x.quote + '"'; }).join(' | ')
        : (c.label !== 'not_checked' ? t('csv_none') : '');
      lines.push(csvLine([c.sku, c.column, c.quote, (c.origin || []).map(function (o) { return found[o]; }).join(' + '),
        [rp.main, rp.rule, rp.note].filter(Boolean).join(' '), ev, labels[c.label] || c.label, fixText(c, true)]));
    });
    return lines.join('\r\n') + '\r\n';
  }

  // ------------------------------------------------------------------ wiring
  function renderAll() {
    renderStatic();
    var d = state.data[state.lang];
    if (!d) return;
    renderReplay(d); renderSummary(d); renderFilters(d); renderCards(d); renderGuard(d); renderInput(d); renderHow();
  }
  function select(lang) {
    state.lang = lang;
    state.types = null;
    state.labels = new Set(LABELS);
    renderStatic();
    $('replay').textContent = t('loading');
    load(lang).then(renderAll).catch(function (e) {
      $('replay').textContent = t('load_error');
      if (window.console) console.error(e);
    });
    try { localStorage.setItem('hcc-lang', lang); } catch (e) { /* storage may be blocked */ }
  }
  function showTab(name) {
    state.tab = name;
    document.querySelectorAll('.tabs button').forEach(function (b) { b.setAttribute('aria-selected', String(b.getAttribute('data-tab') === name)); });
    ['report', 'guard', 'input', 'how'].forEach(function (n) { $('panel-' + n).hidden = n !== name; });
  }

  document.addEventListener('click', function (ev) {
    var el = ev.target.closest('button, a[data-goto]');
    if (!el) return;
    if (el.hasAttribute('data-lang')) { select(el.getAttribute('data-lang')); return; }
    if (el.hasAttribute('data-tab')) { showTab(el.getAttribute('data-tab')); return; }
    var d = state.data[state.lang];
    if (!d) return;
    if (el.hasAttribute('data-flabel')) {
      var l = el.getAttribute('data-flabel');
      if (state.labels.has(l)) state.labels.delete(l); else state.labels.add(l);
      renderFilters(d); renderCards(d); return;
    }
    if (el.hasAttribute('data-ftype')) {
      var x = el.getAttribute('data-ftype');
      if (state.types.has(x)) state.types.delete(x); else state.types.add(x);
      renderFilters(d); renderCards(d); return;
    }
    if (el.hasAttribute('data-goto')) {
      ev.preventDefault();
      state.labels = new Set(LABELS); state.types = null; state.q = ''; $('search').value = '';
      renderFilters(d); renderCards(d); showTab('report');
      var target = document.getElementById('claim-' + el.getAttribute('data-goto'));
      if (target) target.scrollIntoView({ block: 'center' });
      return;
    }
    if (el.id === 'dl-catalog') { download('corrected_catalog_' + state.lang + '.csv', correctedCSV(d)); return; }
    if (el.id === 'dl-findings') { download('findings_' + state.lang + '.csv', findingsCSV(d)); }
  });
  $('search').addEventListener('input', function (e) {
    state.q = e.target.value;
    var d = state.data[state.lang];
    if (d) renderCards(d);
  });

  var start = 'en';
  try { start = localStorage.getItem('hcc-lang') || (/^ko\b/i.test(navigator.language || '') ? 'ko' : 'en'); } catch (e) { start = 'en'; }
  if (/[?&]lang=ko\b/.test(location.search)) start = 'ko';
  if (/[?&]lang=en\b/.test(location.search)) start = 'en';
  if (!EXAMPLES[start]) start = 'en';
  select(start);

  // exposed for the headless check only
  window.__hcc = { correctedCSV: function () { return correctedCSV(state.data[state.lang]); },
                   findingsCSV: function () { return findingsCSV(state.data[state.lang]); }, state: state };
})();
