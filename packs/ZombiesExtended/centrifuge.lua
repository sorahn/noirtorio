
local function swap_entity_light(entity, find, replace)
	for _, working_visualisation in pairs(entity.working_visualisations) do
		if working_visualisation.animation then
			for _, layer in pairs(working_visualisation.animation.layers) do
				-- we don't change the image mod here cause we have already done that
				-- for the base centrifuge
				layer.filename = layer.filename:gsub(find, replace)
				layer.hr_version.filename = layer.hr_version.filename:gsub(find, replace)
			end
		end
	end
end

swap_entity_light(data.raw["assembling-machine"]["centrifuge-mk1"], "centrifuge%-", "centrifuge-mk1-")
swap_entity_light(data.raw["assembling-machine"]["centrifuge-mk2"], "centrifuge%-", "centrifuge-mk2-")
swap_entity_light(data.raw["assembling-machine"]["centrifuge-mk3"], "centrifuge%-", "centrifuge-mk3-")

