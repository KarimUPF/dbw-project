const uniqueProteins = [...new Set(ptmData.map(d => d.gene))];
    const protein1Select = document.getElementById("protein1");
    const protein2Select = document.getElementById("protein2");
    
    uniqueProteins.forEach(protein => {
        let option1 = new Option(protein, protein);
        let option2 = new Option(protein, protein);
        protein1Select.add(option1);
        protein2Select.add(option2);
    });
    
    protein1Select.selectedIndex = 0;
    protein2Select.selectedIndex = uniqueProteins.length > 1 ? 1 : 0;
    
    function updateGraph() {
        const protein1 = protein1Select.value;
        const protein2 = protein2Select.value;
        
        const ptmData1 = ptmData.filter(d => d.gene === protein1);
        const ptmData2 = ptmData.filter(d => d.gene === protein2);
        
        drawGraph(protein1, ptmData1, protein2, ptmData2);
    }
    
    function drawGraph(protein1, ptmData1, protein2, ptmData2) {
        const width = 800, height = 250;
        d3.select("#ptm-graph").html("");
        
        const svg = d3.select("#ptm-graph")
            .attr("width", width)
            .attr("height", height);
        
        const xScale = d3.scaleLinear().domain([0, 100]).range([50, width - 50]);
        const yPositions = [100, 200];

        const proteins = [
            { name: protein1, ptms: ptmData1, y: yPositions[0] },
            { name: protein2, ptms: ptmData2, y: yPositions[1] }
        ];

        proteins.forEach(({ name, ptms, y }) => {
            const lineOffset = 50;
            const ptmOffset = 50;

            svg.append("line")
                .attr("x1", xScale(0) + lineOffset)
                .attr("x2", xScale(100) + lineOffset)
                .attr("y1", y)
                .attr("y2", y)
                .attr("stroke", "black")
                .attr("stroke-width", 2);
            
            svg.append("text")
                .attr("x", 10)
                .attr("y", y + 5)
                .attr("text-anchor", "start")
                .attr("font-size", "16px")
                .attr("fill", "black")
                .text(name);
            
            ptms.forEach(ptm => {
                svg.append("circle")
                    .attr("cx", xScale(ptm.normalized_position) + ptmOffset)
                    .attr("cy", y - 10)
                    .attr("r", 7)
                    .attr("fill", getColor(ptm.modification))
                    .attr("stroke", "black")
                    .attr("stroke-width", 1)
                    .on("mouseover", (event) => showTooltip(event, ptm, name))
                    .on("mouseout", hideTooltip);
            });
        });
    }
    
    function getColor(modification) {
        const modMap = {
            "-p": "Phosphorylation",
            "-ac": "Acetylation",
            "-me": "Methylation",
            "-ub": "Ubiquitination",
            "-sm": "Sumoylation",
            "-oh": "Hydroxylation"
        };
        
        const modFullName = modMap[modification] || "Unknown";
        
        const colorMap = {
            "Phosphorylation": "blue",
            "Acetylation": "green",
            "Methylation": "red",
            "Ubiquitination": "purple",
            "Sumoylation": "pink",
            "Hydroxylation": "brown",
            "Unknown": "gray"
        };
        
        return colorMap[modFullName];
    }
    
    const tooltip = d3.select("#tooltip");

    function showTooltip(event, ptm, protein) {
        tooltip.style("display", "block")
            .style("position", "absolute") // Ensure it's absolute
            .style("left", `${event.pageX + 10}px`)
            .style("top", `${event.pageY - 10}px`)
            .style("background", "white") // Ensure visibility
            .style("border", "1px solid black") // Ensure visibility
            .style("padding", "5px")
            .style("border-radius", "5px")
            .style("z-index", "1000") // Ensure it's on top
            .html(`
                <strong>${protein}</strong><br>
                PTM: ${ptm.modification} (${ptm.residue})<br>
                Original Position: ${ptm.original_position}<br>
                Normalized Position: ${ptm.normalized_position.toFixed(2)}
            `);
    }


    function hideTooltip() {
        tooltip.style("display", "none");
    }

    updateGraph();
    protein1Select.addEventListener("change", updateGraph);
    protein2Select.addEventListener("change", updateGraph);