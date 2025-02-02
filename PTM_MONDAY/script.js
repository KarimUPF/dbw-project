// Import PTM data from ptm_data.js
// Make sure ptm_data.js is included in your HTML file before script.js
// Example: <script src="ptm_data.js"></script>
console.log(ptmData);  // Debugging: Check if the PTM data is loaded correctly

// Extract unique protein names
const uniqueProteins = [...new Set(ptmData.map(d => d.gene))];

// Get dropdown elements
const protein1Select = document.getElementById("protein1");
const protein2Select = document.getElementById("protein2");

// Populate dropdowns
uniqueProteins.forEach(protein => {
    let option1 = new Option(protein, protein);
    let option2 = new Option(protein, protein);
    protein1Select.add(option1);
    protein2Select.add(option2);
});

// Select first two proteins by default
protein1Select.selectedIndex = 0;
protein2Select.selectedIndex = uniqueProteins.length > 1 ? 1 : 0;

// Function to update the graph
function updateGraph() {
    const protein1 = protein1Select.value;
    const protein2 = protein2Select.value;

    // Filter PTM data based on selected proteins
    const ptmData1 = ptmData.filter(d => d.gene === protein1);
    const ptmData2 = ptmData.filter(d => d.gene === protein2);

    drawGraph(protein1, ptmData1, protein2, ptmData2);
}

// Function to draw the graph
function drawGraph(protein1, ptmData1, protein2, ptmData2) {
    const width = 800, height = 250;
    d3.select("#ptm-graph").html(""); // Clear previous graph

    const svg = d3.select("#ptm-graph")
        .attr("width", width)
        .attr("height", height);

    const xScale = d3.scaleLinear().domain([0, 100]).range([50, width - 50]);
    const yPositions = [100, 200];  // Previously [80, 160], now increased spacing
;  // Y positions for each protein line

    const proteins = [
        { name: protein1, ptms: ptmData1, y: yPositions[0] },
        { name: protein2, ptms: ptmData2, y: yPositions[1] }
    ];

    proteins.forEach(({ name, ptms, y }) => {

        const lineOffset = 50;
        const ptmOffset = 50  // Adjust this value to shift the lines to the right

        svg.append("line")
            .attr("x1", xScale(0) + lineOffset)  // Shift start of line right
            .attr("x2", xScale(100) + lineOffset)  // Shift end of line right
            .attr("y1", y)
            .attr("y2", y)
            .attr("stroke", "black")
            .attr("stroke-width", 2);

        svg.append("text")
        .attr("x", 10)  // Move text further left
        .attr("y", y + 5)
        .attr("text-anchor", "start")  // Align text properly
        .attr("font-size", "16px")  // Ensure readable font size
        .attr("fill", "black")  // Ensure visibility
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
//Get color for PTM type
function getColor(modification) {
    // Mapping from dataset suffixes to full modification names
    const modMap = {
        "-p": "Phosphorylation",
        "-ac": "Acetylation",
        "-me": "Methylation",
        "-ub": "Ubiquitination",
        "-sm": "Sumoylation",
        "-oh": "Hydroxylation"
    };

    // Extract the full name using the map
    const modFullName = modMap[modification] || "Unknown";

    // Assign colors based on the full name
    const colorMap = {
        "Phosphorylation": "blue",
        "Acetylation": "green",
        "Methylation": "red",
        "Ubiquitination": "purple",
        "Sumoylation": "pink",
        "Hydroxylation": "brown",
        "Unknown": "gray"  // Default color for unknown PTMs
    };

    return colorMap[modFullName];
}


// Tooltip functions
const tooltip = d3.select("#tooltip");

function showTooltip(event, ptm, protein) {
    tooltip.style("display", "block")
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 10) + "px")
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

// Load initial graph
updateGraph();

// Update graph when selection changes
protein1Select.addEventListener("change", updateGraph);
protein2Select.addEventListener("change", updateGraph);

