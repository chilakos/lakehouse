/**
 * Cube.js configuration for lakehouse semantic layer.
 *
 * Minimal config -- Cube reads YAML model definitions from /cube/conf/model
 * (mounted as a Docker volume from semantic/model). Connection to Trino is
 * configured via environment variables in docker-compose.yml.
 */
module.exports = {
  // Path to Cube YAML model definitions (cubes + views)
  schemaPath: '/cube/conf/model',

  // Disable scheduled refresh in local dev (trigger manually or via Airflow)
  scheduledRefreshTimer: false,

  // Pre-aggregation refresh key interval (5 minutes for local dev)
  scheduledRefreshContexts: () => [{}],
};
