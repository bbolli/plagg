<?xml version="1.0" encoding="iso-8859-1"?>

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">

<!-- $Id: opml.xsl 349 2004-10-25 21:01:47Z bb $ -->

<xsl:output method="xml" indent="no"
  doctype-system="http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd"
  doctype-public="-//W3C//DTD XHTML 1.1//EN"
/>

<xsl:template match="/">
  <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="de">
  <head>
  <title><xsl:value-of select="opml/head/title"/></title>
  <link rel="stylesheet" href="http://www.drbeat.li/bb.css" type="text/css" />
  </head>
  <body><div id="body">
  <xsl:apply-templates/>
  </div></body>
  </html>
</xsl:template>

<xsl:template match="head">
  <div id="header">
  <h1><xsl:value-of select="title"/></h1>
  </div>
</xsl:template>

<xsl:template match="body">
  <div id="main">
  <p>Dies ist meine mehr oder weniger regelm�ssig gelesene Blog-Liste.</p>
  <ul><xsl:apply-templates/></ul>
  <p><code><xsl:value-of select="../head/x-svn-id"/></code></p>
  </div>
</xsl:template>

<xsl:template match="outline">
  <li><xsl:choose>
    <xsl:when test='@htmlUrl != ""'>
      <a href="{@htmlUrl}"><xsl:value-of select="@text"/></a>
    </xsl:when>
    <xsl:otherwise>
      <xsl:value-of select="@text"/>
    </xsl:otherwise>
  </xsl:choose>
  <xsl:choose>
    <xsl:when test='@type = "rss"'> (<a href="{@xmlUrl}">RSS</a>)</xsl:when>
    <xsl:when test='@type = "x-plagg-html"'/>
    <xsl:when test='@type = "x-plagg-computed"'/>
    <xsl:otherwise>
      <ul><xsl:apply-templates/></ul>
    </xsl:otherwise>
  </xsl:choose></li>
</xsl:template>

</xsl:stylesheet>
