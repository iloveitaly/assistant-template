# Change this once to switch MCP add launchers.
MCP_ADD := "node /Users/mike/Projects/javascript/mcp-add"

# Change this once to update the list of clients for all MCP servers.
CLIENTS := "opencode,claude code,antigravity,codex,cursor"

setup-mcp:
	{{MCP_ADD}} --name todoist --type http --url https://ai.todoist.net/mcp --scope project --clients "{{CLIENTS}}"
	{{MCP_ADD}} --name beeper --type http --url http://localhost:23373/v0/mcp --headers "Authorization=Bearer ${BEEPER_MCP_KEY}" --scope project --clients "{{CLIENTS}}"
	{{MCP_ADD}} --name imcp --type stdio --command /Applications/iMCP.app/Contents/MacOS/imcp-server --scope project --clients "{{CLIENTS}}"
	{{MCP_ADD}} --name superhuman-mail --type http --url https://mcp.mail.superhuman.com/mcp --scope project --clients "{{CLIENTS}}"
	{{MCP_ADD}} --name amazon-shopping --type stdio --command "uv --directory /Users/mike/Projects/mcp/amazon-shopping-mcp run --extra camoufox amazon-mcp" --env "AMAZON_BROWSER_BACKEND=camoufox" --scope project --clients "{{CLIENTS}}"
	{{MCP_ADD}} --name browsermcp --type stdio --command "pnpx @browsermcp/mcp@latest" --scope project --clients "{{CLIENTS}}"
	{{MCP_ADD}} --name slack --type stdio --command "pnpx @jtalk22/slack-mcp" --scope project --clients "{{CLIENTS}}"
	{{MCP_ADD}} --name chrome-devtools --type stdio --command "pnpx chrome-devtools-mcp" --scope project --clients "opencode,claude code,antigravity,codex"
	{{MCP_ADD}} --name facebook-marketplace --type stdio --command "node /Users/mike/Projects/ai/personal-assistant/mcps/facebook-marketplace-mcp/dist/index.js" --env "CHROME_PROFILE=Profile 12" --scope project --clients "{{CLIENTS}}"
	{{MCP_ADD}} --name bargainer --type stdio --command "node /Users/mike/Projects/javascript/bargainer-mcp-client/dist/index.js" --scope project --clients "{{CLIENTS}}"
	{{MCP_ADD}} --name camofox-browser --type stdio --command "pnpx @askjo/camofox-browser-mcp" --scope project --clients "{{CLIENTS}}"
	{{MCP_ADD}} --name costco --type stdio --command "uv --directory /Users/mike/Projects/ai/costco-mcp run costco-mcp-server" --scope project --clients "{{CLIENTS}}"

# run the foreground scheduler for cron.yml
cron:
    ./scripts/cron.py

# catch up due jobs when the workspace wakes
initial_wake:
    ./scripts/cron.py --once
