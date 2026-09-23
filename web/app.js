const currency = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' });
const money = n => currency.format(n);
const text = (tag, value, className = '') => {
  const node = document.createElement(tag);
  node.textContent = value;
  node.className = className;
  return node;
};

async function refresh() {
  const status = document.querySelector('#status').value;
  const responses = await Promise.all([fetch('/api/overview'), fetch(`/api/invoices?status=${status}`)]);
  if (responses.some(r => !r.ok)) throw new Error('Could not refresh the register.');
  const [data, rows] = await Promise.all(responses.map(r => r.json()));
  document.querySelector('#invoice-count').textContent = data.summary.invoice_count;
  document.querySelector('#open-count').textContent = data.summary.open_count;
  document.querySelector('#outstanding').textContent = money(data.summary.outstanding);
  const body = document.querySelector('#invoices');
  body.replaceChildren();
  rows.forEach(r => {
    const row = document.createElement('tr');
    [r.customer_name, r.invoice_number, r.due_date].forEach(v => row.append(text('td', v)));
    [r.amount, r.paid, r.balance].forEach(v => row.append(text('td', money(v), 'number')));
    row.append(text('td', r.status));
    body.append(row);
  });
  const unmatched = document.querySelector('#unmatched');
  unmatched.replaceChildren(...data.unmatched_payments.map(p => text('li', `${p.payment_id} · ${p.customer_id} / ${p.invoice_number} · ${money(p.amount)}`)));
  if (!data.unmatched_payments.length) unmatched.append(text('li', 'No unmatched payments.'));
  document.querySelector('#page-error').textContent = '';
}

async function submitImport(form) {
  const feedback = form.querySelector('.feedback');
  const button = form.querySelector('button');
  button.disabled = true;
  feedback.replaceChildren(text('span', 'Importing…'));

  try {
    const fileInput = form.querySelector('input');
    if (!fileInput.files || !fileInput.files.length) {
      throw new Error('Please select a CSV file to import.');
    }
    const selectedFile = fileInput.files[0];
    const csv = await selectedFile.text();
    const headers = { 'Content-Type': 'text/csv' };
    if (selectedFile.name) {
      headers['X-Import-Filename'] = selectedFile.name;
    }
    const res = await fetch(`/api/import?kind=${form.dataset.kind}`, {
      method: 'POST',
      headers: headers,
      body: csv
    });

    let data;
    try {
      data = await res.json();
    } catch {
      throw new Error('Server returned an invalid response.');
    }

    if (!res.ok) {
      const errorMsg = (data && data.error) ? data.error : `Server returned HTTP ${res.status}.`;
      feedback.replaceChildren(text('span', `Import failed: ${errorMsg}`));
      return;
    }

    const summaryText = `Import processed: ${data.imported} imported, ${data.skipped} skipped, ${data.rejected} rejected.`;
    const container = document.createElement('div');
    container.append(text('span', summaryText));

    if (data.rejected > 0 && Array.isArray(data.errors) && data.errors.length) {
      const errList = document.createElement('ul');
      data.errors.forEach(err => {
        errList.append(text('li', `Line ${err.line}: ${err.reason}`));
      });
      container.append(errList);
    }

    feedback.replaceChildren(container);
    await refresh();
  } catch (error) {
    feedback.replaceChildren(text('span', `Import failed: ${error.message}`));
  } finally {
    button.disabled = false;
  }
}



document.querySelector('#status').addEventListener('change', () => refresh().catch(e => { document.querySelector('#page-error').textContent = e.message; }));
document.querySelectorAll('form[data-kind]').forEach(form => form.addEventListener('submit', e => { e.preventDefault(); submitImport(form); }));
refresh().catch(e => { document.querySelector('#page-error').textContent = e.message; });
