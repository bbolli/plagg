<?xml version="1.0" encoding="utf-8"?>

<xsl:stylesheet
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0"
  xmlns="http://www.w3.org/1999/xhtml"
>

<!-- $Id: opml.xsl 349 2004-10-25 21:01:47Z bb $ -->

<xsl:output method="xml" indent="yes"
  doctype-system="http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd"
  doctype-public="-//W3C//DTD XHTML 1.1//EN"
/>

<xsl:template match="/">
  <xsl:processing-instruction name="xml-stylesheet">href="/bb.css" type="text/css" title="2b style"</xsl:processing-instruction>
  <html>
  <head>
  <title><xsl:value-of select="opml/head/title"/></title>
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
  <ul><xsl:apply-templates/></ul>
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
  <xsl:if test='@xmlUrl != ""'> (<a href="{@xmlUrl}">RSS</a>)</xsl:if>
  <xsl:choose>
    <xsl:when test='@type = "rss"'/>
    <xsl:when test='@type = "x-plagg-html"'/>
    <xsl:when test='@type = "x-plagg-computed"'/>
    <xsl:otherwise>
      <ul><xsl:apply-templates/></ul>
    </xsl:otherwise>
  </xsl:choose></li>
</xsl:template>

</xsl:stylesheet>
