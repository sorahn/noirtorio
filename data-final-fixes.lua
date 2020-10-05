local config = require("config")


local split = function(in_str, delim)
    local list = {};
    for match in (in_str..delim):gmatch("(.-)"..delim) do
        table.insert(list, match);
    end
    return list;
end

local concat = function(list1, list2)
	local new_list = {}
	for index,item in pairs(list1) do
		new_list[#new_list + 1] = item
	end
	for index,item in pairs(list2) do
		new_list[#new_list + 1] = item
	end
	return new_list
end

isReplaceItem = function(path, step)
	step = step or 1
	local split_path = split(path:gsub("__", ""), "/")

	configdata = config.data
	for i=1,step do
		if not(i == step) then
			configdata = configdata[split_path[i]]
		end
	end

	local count = 0
	for key,item in pairs(configdata) do
		--log(key .. )
		count = count + 1
		if (key == split_path[step]) then
			return isReplaceItem(path, step + 1)

		elseif (item == split_path[step]) then
			return true
		end
	end
	if (count == 0) then
		return true
	end
	return false
end

checkData = function(path)
	--local builder = ""
	--for index,key in pairs(path) do
	--	builder  = builder .. key .. ", "
	--end
	--log(builder)

	local pathed_data = data.raw
	for index,key in pairs(path) do
		pathed_data = pathed_data[key]
	end

	for key,item in pairs(pathed_data) do
		if (type(item) == "string") then
			local itemtype = split(item, "%p")

			if not(itemtype[3] == config.resource_pack_name) then
				itemtype = itemtype[#itemtype]
				if (itemtype == "png" or itemtype == "jpg" or itemtype == "ogg") then
					if (isReplaceItem(item)) then
						--log(item)
						local changed_item_path = "__" .. config.resource_pack_name .. "__/data/" .. item:gsub("__", "")
						--log(changed_item_path)
						pathed_data[key] = changed_item_path
					end
				end
			end	
		elseif (type(item) == "table") then
			--log(tostring(key) .. " " .. type(item))
			--log(tostring(#concat(path, {key})))
			checkData(concat(path, {key}))
		end
	end
end

if not(next(config.data) == nil) then
	checkData({})
end




-- desaturate the map
local function desaturate(c, sat, bri)
	-- colors can be either named, on indexed. They also can be valued [0-1] or [0-255], but that doesn't matter for this maths
	r = c.r or c[1]
	g = c.g or c[2]
	b = c.b or c[3]
	a = c.a or c[4] or 1

	-- from: https://www.w3.org/TR/filter-effects-1/#feColorMatrixElement
	ret = {
		r = (r*(0.213 + 0.787*sat) + g*(0.715 - 0.715*sat) + b*(0.072 - 0.072*sat)) * bri,
		g = (r*(0.213 - 0.213*sat) + g*(0.715 + 0.285*sat) + b*(0.072 - 0.072*sat)) * bri,
		b = (r*(0.213 - 0.213*sat) + g*(0.715 - 0.715*sat) + b*(0.072 + 0.928*sat)) * bri,
		a = a,
	}

	return ret
end


for entity_group_name, entity_group in pairs(data.raw) do
	for _, entity in pairs(entity_group) do
		if entity.map_color ~= nil then
			entity.map_color = desaturate(entity.map_color, 0.1, 0.7)
		end

		if entity.friendly_map_color ~= nil then
			entity.friendly_map_color = desaturate(entity.friendly_map_color, 0.1, 0.7)
		end

		if entity.enemy_map_color ~= nil then
			entity.enemy_map_color = desaturate(entity.enemy_map_color, 0.1, 0.7)
		end
	end
end


-- There are a bunch of default colors in UtilityConstants.chart for the map that we must desaturate too
local function desaturate_table(t, sat, bri, postfix)
	for k, v in pairs(t) do
		if postfix == nil or k:sub(-#postfix) == postfix then
			t[k] = desaturate(t[k], sat, bri)
		end
	end
end
desaturate_table(data.raw["utility-constants"].default.chart, 0.1, 0.7, "_color")
desaturate_table(data.raw["utility-constants"].default.chart.default_color_by_type, 0.1, 0.7)
desaturate_table(data.raw["utility-constants"].default.chart.default_friendly_color_by_type, 0.1, 0.7)


