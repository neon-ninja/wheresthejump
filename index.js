
const { addonBuilder, serveHTTP } = require("stremio-addon-sdk");
const fs = require("fs");
const path = require("path");
const Papa = require("papaparse");

const manifest = {
  id: "org.stremio.wheresthejump",
  version: "1.0.1",
  name: "Where's The Jump",
  description: "Adds jump scare information and subtitles from wheresthejump.com. Open source at <a href='https://github.com/neon-ninja/wheresthejump'>https://github.com/neon-ninja/wheresthejump</a>",
  resources: ["stream", "subtitles"],
  types: ["movie", "series"],
  idPrefixes: ["tt"], // IMDb IDs
  catalogs: []
};

const builder = new addonBuilder(manifest);

// Load jump scare info from CSV using papaparse
function loadJumpScareInfo() {
  const csvPath = path.join(__dirname, "wheresthejump.csv");
  if (!fs.existsSync(csvPath)) return {};
  const data = fs.readFileSync(csvPath, "utf8");
  const parsed = Papa.parse(data, { header: true, skipEmptyLines: true });
  const info = {};
  for (const row of parsed.data) {
    const imdb = row["IMDB"]?.trim();
    if (imdb) {
      info[imdb] = {
        movie: row["Movie Name"],
        director: row["Director"],
        year: row["Year"],
        jumpCount: row["Jump Count"],
        jumpRating: row["Jump Scare Rating"],
        summary: row["Summary"],
        rating: row["Rating"],
        srtLink: row["SRT Link"],
        url: row["URL"]
      };
    }
  }
  return info;
}

const jumpScareData = loadJumpScareInfo();
console.log(jumpScareData);

builder.defineStreamHandler(async ({ type, id }) => {
  id = id.split(":")[0]; // IMDb ID
  const jumpInfo = jumpScareData[id];
  const description = `${jumpInfo.summary}\n${jumpInfo.rating}`;
  return {
    streams: [{
      name: "WheresTheJump?",
      description,
      externalUrl: jumpInfo.url
    }],
  };
});

// Subtitles handler for SRT files
builder.defineSubtitlesHandler(async ({ type, id }) => {
  id = id.split(":")[0]; // IMDb ID
  const jumpInfo = jumpScareData[id];
  let srtFile = jumpInfo.srtLink.replace("https://wheresthejump.com/subtitles/", "");
  if (!srtFile) {
    return { subtitles: [] };
  }
  let srtUrl = `https://raw.githubusercontent.com/neon-ninja/wheresthejump/refs/heads/main/srt/` + srtFile
  return {
    subtitles: [
      {
        id: `wheresthejump-merged-${id}`,
        url: srtUrl.replace(".srt", "_merged.srt"),
        lang: "en",
        name: "Jump Scare + EN SRT"
      },
      {
        id: `wheresthejump-${id}`,
        url: srtUrl,
        lang: "en",
        name: "Jump Scare SRT"
      }
    ],
  };
});

// Serve SRT files
serveHTTP(builder.getInterface(), { port: process.env.PORT || 7000 });
