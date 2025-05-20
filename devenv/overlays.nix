[
  # Accept SSPL license (ex: MongoDB) as 'free' (debated in upstream (?))
  (final: prev: {
    stdenv = prev.stdenv.override {
      config = prev.config // {
        allowlistedLicenses = [ prev.lib.licenses.sspl ];
      };
    };
  })
]
