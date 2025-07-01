module.exports = function(eleventyConfig) {
  // Copy static assets
  eleventyConfig.addPassthroughCopy("src/assets");

  // Add custom filter for fixed decimal places
  eleventyConfig.addFilter("toFixed", function(value, decimals) {
    if (value === null || value === undefined || isNaN(value)) {
      return '-';
    }
    return Number(value).toFixed(decimals);
  });

  // Set template formats
  eleventyConfig.setTemplateFormats([
    "md", "njk", "html", "liquid"
  ]);

  // Set directories
  return {
    dir: {
      input: "src",
      output: "_site",
      includes: "_includes",
      layouts: "_layouts",
      data: "_data"
    },
    templateFormats: ["njk", "md", "html"],
    htmlTemplateEngine: "njk",
    markdownTemplateEngine: "njk"
  };
};