local config = require("config")

-- replace all files mentioned in the config file
local function checkData(table)
	for key, item in pairs(table) do
		if type(item) == "string" then
			if config.updated_assets[item] ~= nil then
				local changed_item_path = "__" .. config.resource_pack_name .. "__/data/" .. item
				table[key] = changed_item_path
			end
		elseif type(item) == "table" then
			checkData(item)
		end
	end
end

checkData(data.raw)

