local function desaturate(c, bri, sat)
	if c == nil then
		return nil
	end

	-- colors can be either named, on indexed
	r = c.r or c[1]
	g = c.g or c[2]
	b = c.b or c[3]
	a = c.a or c[4]

	-- They can also be valued [0-1] or [0-255]
	if r > 1 or g > 1 or b > 1 or (a or 1) > 1 then
		r = r / 255
		g = g / 255
		b = b / 255
		if a ~= nil then
			a = a / 255
		end
	end

	-- Numbers taken from factorio's shader. Keep in sync with run-conversion.py
	ret = {
		r = (r*(0.3086 + 0.6914*sat) + g*(0.6094 - 0.6094*sat) + b*(0.0820 - 0.0820*sat)) * bri,
		g = (r*(0.3086 - 0.3086*sat) + g*(0.6094 + 0.3906*sat) + b*(0.0820 - 0.0820*sat)) * bri,
		b = (r*(0.3086 - 0.3086*sat) + g*(0.6094 - 0.6094*sat) + b*(0.0820 + 0.9180*sat)) * bri,
		a = a,
	}

	local max = math.max(ret.r, ret.g, ret.b)
	if max > 1 then
		-- we have been upscaled past the maximum brightness :(.
		-- Reduce it down so factorio doesn't think we are using [0-255] colors
		-- TODO: is this better than saturating the channel?
		ret.r = ret.r / max
		ret.g = ret.g / max
		ret.b = ret.b / max
	end

	return ret
end

local function scale_table(table, a)
	for key, value in pairs(table) do
		table[key] = table[key] * a
	end
end

for entity_group_name, entity_group in pairs(data.raw) do
	for _, entity in pairs(entity_group) do
		entity.map_color = desaturate(entity.map_color, 0.7, 0.1)
		entity.friendly_map_color = desaturate(entity.friendly_map_color, 0.7, 0.1)
		entity.enemy_map_color = desaturate(entity.enemy_map_color, 0.7, 0.1)

		-- fixup the drawing of water
		if entity.name == 'water-green' or entity.name == 'deepwater-green' then
			entity.effect_color = desaturate(entity.effect_color, 0.5, 0.3)
			entity.effect_color_secondary = desaturate(entity.effect_color_secondary, 0.5, 0.3)
		else
			entity.effect_color = desaturate(entity.effect_color, 0.5, 0.6)
                        entity.effect_color_secondary = desaturate(entity.effect_color_secondary, 0.5, 0.6)
		end

		if entity.foam_color ~= nil then
			entity.foam_color = desaturate(entity.foam_color, 0.5, 0.6)

			-- since we have made the tiles darker, we also must drop all of the thresholds
			scale_table(entity.dark_threshold, 0.5)
			scale_table(entity.reflection_threshold, 0.5)
			scale_table(entity.specular_threshold, 0.5)
		end

		-- move some alt-mode module locations
		if type(entity.name) == "string" and entity.module_specification ~= nil then
			if entity.name:sub(1, #"chemical-plant") == "chemical-plant" then
				entity.module_specification.module_info_icon_shift = {0, -1.0}
			end
			if entity.name:sub(1, #"electric-furnace") == "electric-furnace" then
				entity.module_specification.module_info_icon_shift = {0, -0.9}
			end
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
desaturate_table(data.raw["utility-constants"].default.chart, 0.7, 0.1, "_color")
desaturate_table(data.raw["utility-constants"].default.chart.default_color_by_type, 0.7, 0.1)
desaturate_table(data.raw["utility-constants"].default.chart.default_friendly_color_by_type, 0.7, 0.1)


