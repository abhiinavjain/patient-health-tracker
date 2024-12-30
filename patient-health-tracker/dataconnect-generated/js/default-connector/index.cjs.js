const { getDataConnect, validateArgs } = require('firebase/data-connect');

const connectorConfig = {
  connector: 'default',
  service: 'patient-health-tracker',
  location: 'us-central1'
};
exports.connectorConfig = connectorConfig;

